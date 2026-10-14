#pragma once
// Small local harness parser. Integer-only JSON numbers, no external dependency.
#include <cctype>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
namespace local_json {
struct Value {
  enum Kind {Null, Boolean, Number, String, Array, Object} kind=Null;
  int64_t number=0; bool boolean=false; std::string string;
  std::vector<Value> array; std::map<std::string,Value> object;
  const Value& at(const std::string& key)const {if(kind!=Object || !object.count(key))throw std::runtime_error("Missing JSON field: "+key);return object.at(key);}
  int64_t integer()const {if(kind!=Number)throw std::runtime_error("Expected integer JSON number");return number;}
  const std::string& text()const {if(kind!=String)throw std::runtime_error("Expected JSON string");return string;}
  const std::vector<Value>& list()const {if(kind!=Array)throw std::runtime_error("Expected JSON array");return array;}
};
class Parser {
  const std::string& source;size_t pos=0;int depth=0;
  void space(){while(pos<source.size() && std::isspace(static_cast<unsigned char>(source[pos])))++pos;}
  bool take(char c){space();if(pos<source.size() && source[pos]==c){++pos;return true;}return false;}
  [[noreturn]] void error()const {throw std::runtime_error("Invalid JSON at byte "+std::to_string(pos));}
  unsigned hex(){if(pos>=source.size())error();char c=source[pos++];if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;error();}
  std::string quoted(){
    if(!take('"'))error();std::string out;
    while(pos<source.size()) {
      char c=source[pos++];if(c=='"')return out;if(static_cast<unsigned char>(c)<32)error();
      if(c!='\\'){out+=c;continue;}if(pos>=source.size())error();c=source[pos++];
      if(c=='"'||c=='\\'||c=='/')out+=c;
      else if(c=='n')out+='\n';else if(c=='r')out+='\r';else if(c=='t')out+='\t';else if(c=='b')out+='\b';else if(c=='f')out+='\f';
      else if(c=='u') {
        unsigned code=0;for(int k=0;k<4;++k)code=code*16+hex();
        if(code>=0xd800 && code<=0xdbff){if(pos+2>source.size() || source[pos]!='\\' || source[pos+1]!='u')error();pos+=2;unsigned low=0;for(int k=0;k<4;++k)low=low*16+hex();if(low<0xdc00 || low>0xdfff)error();code=0x10000+(code-0xd800)*1024+low-0xdc00;}
        else if(code>=0xdc00 && code<=0xdfff)error();
        if(code<0x80)out+=static_cast<char>(code);
        else if(code<0x800){out+=static_cast<char>(0xc0|(code>>6));out+=static_cast<char>(0x80|(code&63));}
        else if(code<0x10000){out+=static_cast<char>(0xe0|(code>>12));out+=static_cast<char>(0x80|((code>>6)&63));out+=static_cast<char>(0x80|(code&63));}
        else {out+=static_cast<char>(0xf0|(code>>18));out+=static_cast<char>(0x80|((code>>12)&63));out+=static_cast<char>(0x80|((code>>6)&63));out+=static_cast<char>(0x80|(code&63));}
      } else error();
    }error();
  }
  Value value(){
    space();if(++depth>256 || pos>=source.size())error();Value v;
    if(source[pos]=='"'){v.kind=Value::String;v.string=quoted();}
    else if(take('{')) {v.kind=Value::Object;if(!take('}'))do{auto key=quoted();if(!take(':'))error();if(!v.object.emplace(key,value()).second)error();if(take('}'))break;if(!take(','))error();}while(true);}
    else if(take('[')) {v.kind=Value::Array;if(!take(']'))do{v.array.push_back(value());if(take(']'))break;if(!take(','))error();}while(true);}
    else if(source.compare(pos,4,"true")==0){pos+=4;v.kind=Value::Boolean;v.boolean=true;}
    else if(source.compare(pos,5,"false")==0){pos+=5;v.kind=Value::Boolean;}
    else if(source.compare(pos,4,"null")==0)pos+=4;
    else {size_t begin=pos;if(source[pos]=='-')++pos;if(pos>=source.size() || !std::isdigit(static_cast<unsigned char>(source[pos])))error();if(source[pos]=='0')++pos;else while(pos<source.size()&&std::isdigit(static_cast<unsigned char>(source[pos])))++pos;v.kind=Value::Number;try{v.number=std::stoll(source.substr(begin,pos-begin));}catch(...){error();}}
    --depth;return v;
  }
public:
  explicit Parser(const std::string& s):source(s){}
  Value parse(){auto result=value();space();if(pos!=source.size())error();return result;}
};
inline std::string quote(const std::string& s){std::string out="\"";const char* hex="0123456789abcdef";for(unsigned char c:s){if(c=='"'||c=='\\'){out+='\\';out+=static_cast<char>(c);}else if(c<32){out+="\\u00";out+=hex[c>>4];out+=hex[c&15];}else out+=static_cast<char>(c);}return out+'"';}
inline std::string dump(const Value& v){
  if(v.kind==Value::Null)return "null";if(v.kind==Value::Boolean)return v.boolean?"true":"false";if(v.kind==Value::Number)return std::to_string(v.number);if(v.kind==Value::String)return quote(v.string);
  std::string out=v.kind==Value::Array?"[":"{";bool first=true;
  if(v.kind==Value::Array)for(const auto& x:v.array){if(!first)out+=',';first=false;out+=dump(x);}
  else for(const auto& [k,x]:v.object){if(!first)out+=',';first=false;out+=quote(k)+':'+dump(x);}
  return out+(v.kind==Value::Array?']':'}');
}
} // namespace local_json
