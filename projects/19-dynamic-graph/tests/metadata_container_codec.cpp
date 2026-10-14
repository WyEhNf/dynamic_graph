// Independent native zlib encoder and production decoder for cross-language tests.
#include "cholesky/compressed_metadata.hpp"
#include "cholesky/runtime.hpp"
#include <bit>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <zlib.h>
int main(int argc,char** argv) {
  try {
    if(argc!=4)throw std::runtime_error("mode input output required");
    std::ifstream in(argv[2],std::ios::binary);
    if(!in)throw std::runtime_error("cannot open input");
    std::string data((std::istreambuf_iterator<char>(in)),{}),output;
    const std::string mode=argv[1];
    if(mode=="decode")output=chol::decode_metadata_container(data);
    else if(mode=="parse") { auto m=chol::read_metadata(argv[2]);output=m.algorithm; }
    else if(mode=="parsebits") {
      const auto m=chol::read_metadata(argv[2]);if(m.program.empty())throw std::runtime_error("missing constant");
      const auto bits=std::bit_cast<std::uint64_t>(m.program[0].argument);
      for(unsigned i=0;i<8;++i)output.push_back(static_cast<char>((bits>>(8*i))&255));
    }
    else if(mode=="encode") {
      if(data.empty()||data.size()>16u*1024u*1024u)throw std::runtime_error("input bound");
      output="DYNCHZ01";
      uLongf size=compressBound(data.size());std::string payload(size,'\0');
      if(compress2(reinterpret_cast<Bytef*>(payload.data()),&size,reinterpret_cast<const Bytef*>(data.data()),data.size(),9)!=Z_OK)throw std::runtime_error("compress failure");
      if(size>16u*1024u*1024u)throw std::runtime_error("payload bound");
      for(const auto n:{static_cast<unsigned long>(data.size()),static_cast<unsigned long>(size)})
        for(unsigned i=0;i<4;++i)output.push_back(static_cast<char>((n>>(8*i))&255));
      payload.resize(size);output+=payload;
    } else throw std::runtime_error("unknown mode");
    std::ofstream out(argv[3],std::ios::binary);out.write(output.data(),output.size());
    if(!out)throw std::runtime_error("output failure");
    return 0;
  } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
