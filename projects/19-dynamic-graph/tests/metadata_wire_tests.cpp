#include "cholesky/runtime.hpp"
#include <array>
#include <bit>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>

void require(bool ok,const char* message) { if(!ok)throw std::runtime_error(message); }
int main() {
 try {
  const auto path=std::filesystem::temp_directory_path()/"dynchol-wire-protocol-test.meta";
  const std::string fields="algorithm=ast_vm_v2\narithmetic=fp64_source_order_no_implicit_fma\ndependencies=source_control_flow\noptimized=none\nslots=3\nshape_slot=0\nblock_slot=-1\n";
  auto read=[&](const std::string& schema,const std::string& body,const std::string& encoding="bytecode_encoding=base36_opcode_v1\n") {
    {std::ofstream out(path);out<<schema<<'\n'<<fields<<encoding<<"PROGRAM\n"<<body;}
    return chol::read_metadata(path.string());
  };
  // Independent literal golden list, deliberately not imported from the reader.
  const std::array<chol::Opcode,33> expected{chol::Opcode::Const,chol::Opcode::Load,chol::Opcode::Store,chol::Opcode::Uninit,chol::Opcode::Read,chol::Opcode::Write,chol::Opcode::Dup,chol::Opcode::Pop,chol::Opcode::Add,chol::Opcode::Sub,chol::Opcode::Mul,chol::Opcode::Div,chol::Opcode::IntDiv,chol::Opcode::Mod,chol::Opcode::Neg,chol::Opcode::Not,chol::Opcode::Bool,chol::Opcode::Trunc,chol::Opcode::Sqrt,chol::Opcode::Abs,chol::Opcode::Min,chol::Opcode::Max,chol::Opcode::Fma,chol::Opcode::Lt,chol::Opcode::Le,chol::Opcode::Gt,chol::Opcode::Ge,chol::Opcode::Eq,chol::Opcode::Ne,chol::Opcode::Jump,chol::Opcode::Jz,chol::Opcode::Jnz,chol::Opcode::Return};
  const std::string golden="0 -0.0\n1 1\n2 1\n3 1\n4 0\n5 1\n6\n7\n8\n9\nA\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\nM\nN\nO\nP\nQ\nR\nS\nT 0\nU 0\nV 0\nW\n";
  const auto parsed=read("DYNCHOL 3",golden);
  require(parsed.program.size()==33,"golden length");
  for(std::size_t i=0;i<expected.size();++i)require(parsed.program[i].opcode==expected[i],"wire mapping mismatch");
  require(std::signbit(parsed.program[0].argument),"negative zero lost");
  // Independent literal IEEE754 goldens: compare the native parser, not text.
  const std::array<std::pair<const char*,std::uint64_t>,6> constants{{
    {"+0.0",UINT64_C(0x0000000000000000)},
    {"-0.0",UINT64_C(0x8000000000000000)},
    {"5e-324",UINT64_C(0x0000000000000001)},
    {"2.2250738585072014e-308",UINT64_C(0x0010000000000000)},
    {"1.7976931348623157e308",UINT64_C(0x7fefffffffffffff)},
    {"9007199254740993.0",UINT64_C(0x4340000000000000)}}};
  for(const auto& [token,bits]:constants) {
    const auto named=read("DYNCHOL 2",std::string("CONST ")+token+"\nRETURN\n","");
    const auto wire=read("DYNCHOL 3",std::string("0 ")+token+"\nW\n");
    require(std::bit_cast<std::uint64_t>(named.program[0].argument)==bits,"v2 numeric bits differ from golden");
    require(std::bit_cast<std::uint64_t>(wire.program[0].argument)==bits,"v3 numeric bits differ from golden");
  }
  const std::array<std::string,26> bad{"", "X", "Y", "Z", "a", "00 1", "CONST 0", "0", "8 0", "8 ", "0  1", "0 1 ", "0 1 2", "0 nan", "0 inf", "0 1e999", "0 0x1p0", "0 .", "0 1e", "0 +", "1 3", "1 -1", "T 99", "4 2", "5 0", "0\t1"};
  for(const auto& row:bad) {
    bool rejected=false;try{(void)read("DYNCHOL 3",row+"\nW\n");}catch(const std::exception&){rejected=true;}
    require(rejected,"malformed wire accepted");
  }
  for(const auto& encoding: {std::string(),std::string("bytecode_encoding=unknown\n")}) {
    bool rejected=false;try{(void)read("DYNCHOL 3","0 0\nW\n",encoding);}catch(const std::exception&){rejected=true;}require(rejected,"bad encoding accepted");
  }
  const auto v2=read("DYNCHOL 2","CONST -0.0\nRETURN 0\n","");
  require(v2.program[0].opcode==chol::Opcode::Const&&std::signbit(v2.program[0].argument),"v2 compatibility failed");
  bool rejected=false;try{(void)read("DYNCHOL 2","0 0\nW\n");}catch(const std::exception&){rejected=true;}require(rejected,"v2 wire confusion accepted");
  {std::ofstream out(path);out<<"DYNCHOL 1\nalgorithm=cholesky_column_v1\narithmetic=fp64_ascending_k_no_fma\ndependencies=column_barrier_diagonal_then_rows\n";}
  require(chol::read_metadata(path.string()).program.empty(),"v1 compatibility failed");
  std::filesystem::remove(path);
  std::cout<<"33 golden opcode mappings, 12 native IEEE754 bit goldens, 29 rejections and v1/v2 compatibility passed\n";
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
