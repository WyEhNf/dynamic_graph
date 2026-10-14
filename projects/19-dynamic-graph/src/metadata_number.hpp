#pragma once
#include <string_view>
namespace chol::detail {
// The exact ASCII grammar of base36_opcode_v1's decimal argument token.
// This recognizes text only. The existing locale/fenv-aware stream still
// performs conversion, preserving subnormals, rounding and error behavior.
inline bool canonical_metadata_number(std::string_view text) noexcept {
  std::size_t p=0;
  if(p<text.size()&&(text[p]=='+'||text[p]=='-'))++p;
  const auto digits=[&] {
    const auto start=p;
    while(p<text.size()&&text[p]>='0'&&text[p]<='9')++p;
    return p-start;
  };
  const auto whole=digits();
  std::size_t fraction=0;
  if(p<text.size()&&text[p]=='.'){++p;fraction=digits();}
  if(whole+fraction==0)return false;
  if(p<text.size()&&(text[p]=='e'||text[p]=='E')) {
    ++p;
    if(p<text.size()&&(text[p]=='+'||text[p]=='-'))++p;
    if(digits()==0)return false;
  }
  return p==text.size();
}
}
