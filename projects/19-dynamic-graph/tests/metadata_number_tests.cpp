#include "metadata_number.hpp"
#include <iostream>
#include <regex>
#include <string>
#include <random>

int main() {
  const std::regex oracle(R"(^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$)");
  std::size_t checked=0;
  auto check=[&](const std::string& s) {
    ++checked;
    if (chol::detail::canonical_metadata_number(s)!=std::regex_match(s,oracle)) {
      std::cerr << "number grammar mismatch, length=" << s.size() << '\n';
      return false;
    }
    return true;
  };
  const std::string alphabet="01+-.eE x";
  auto walk=[&](auto&& self,std::string& s,int left)->bool {
    if(!check(s))return false;
    if(!left)return true;
    for(char c:alphabet) {s.push_back(c);if(!self(self,s,left-1))return false;s.pop_back();}
    return true;
  };
  std::string s;
  if(!walk(walk,s,5))return 1;
  std::mt19937 random(190034);
  for(int i=0;i<30000;++i) {
    s.clear();const int length=random()%65;
    for(int j=0;j<length;++j)s.push_back(static_cast<char>(random()%256));
    if(!check(s))return 2;
  }
  for(const auto* token:{"-0","+.0","1.","1e-324","2.2250738585072014e-308","1.7976931348623157e+308","nan","inf","0x1p0","1e","1,2"})
    if(!check(token))return 3;
  if(!chol::detail::canonical_metadata_number(std::string(100000,'1')) ||
      chol::detail::canonical_metadata_number(std::string(100000,'1')+"x"))return 4;
  std::cout << "metadata grammar cases=" << checked << "; long-token checks=2\n";
}
