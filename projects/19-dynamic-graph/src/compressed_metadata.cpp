#include "cholesky/compressed_metadata.hpp"
#include <array>
#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <zlib.h>
namespace chol {
namespace {
constexpr std::string_view magic="DYNCHZ01";
constexpr std::uint32_t limit=16u*1024u*1024u;
std::uint32_t little32(std::string_view data,std::size_t offset) {
  std::uint32_t n=0;
  for(std::size_t i=0;i<4;++i)n|=static_cast<std::uint32_t>(static_cast<unsigned char>(data[offset+i]))<<(8*i);
  return n;
}
}
std::string decode_metadata_container(std::string_view bytes) {
  if(bytes.size()<16||bytes.substr(0,8)!=magic)throw std::runtime_error("invalid compressed metadata header");
  const auto raw=little32(bytes,8),size=little32(bytes,12);
  if(raw==0||raw>limit||size<6||size>limit||bytes.size()!=16u+size)throw std::runtime_error("compressed metadata size mismatch");
  // Allocate one extra byte to detect expansion beyond the declared size.
  std::string output(static_cast<std::size_t>(raw)+1,'\0');
  z_stream stream{};
  stream.next_in=reinterpret_cast<Bytef*>(const_cast<char*>(bytes.data()+16));
  stream.avail_in=size;
  stream.next_out=reinterpret_cast<Bytef*>(output.data());
  stream.avail_out=raw+1;
  if(inflateInit2(&stream,15)!=Z_OK)throw std::runtime_error("cannot initialize metadata inflater");
  const int status=inflate(&stream,Z_FINISH);
  const bool valid=status==Z_STREAM_END&&stream.total_out==raw&&stream.total_in==size&&stream.avail_in==0;
  inflateEnd(&stream);
  if(!valid)throw std::runtime_error("invalid compressed metadata stream or decoded length");
  output.resize(raw);
  return output;
}
std::optional<std::string> read_compressed_metadata(const std::string& path) {
  std::ifstream file(path,std::ios::binary);
  if(!file)throw std::runtime_error("cannot open metadata: "+path);
  std::array<char,8> head{};file.read(head.data(),head.size());
  if(file.gcount()!=8||std::string_view(head.data(),head.size())!=magic)return std::nullopt;
  file.clear();file.seekg(0,std::ios::end);const auto size=file.tellg();
  if(size<16||size>static_cast<std::streamoff>(limit+16))throw std::runtime_error("compressed metadata file size out of bounds");
  file.seekg(0);std::string data(static_cast<std::size_t>(size),'\0');
  if(!file.read(data.data(),size))throw std::runtime_error("compressed metadata short read");
  return decode_metadata_container(data);
}
}
