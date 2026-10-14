#include "cholesky/runtime.hpp"
#include <array>
#include <bit>
#include <cmath>
#include <stdexcept>

namespace chol {
namespace {
template<class T> T read_little(std::istream& in) {
  static_assert(std::endian::native == std::endian::little, "local binary fixture assumes little endian");
  T value{};
  in.read(reinterpret_cast<char*>(&value), sizeof(T));
  if (!in) throw std::runtime_error("truncated binary input");
  return value;
}
template<class T> void write_little(std::ostream& out, T value) {
  out.write(reinterpret_cast<const char*>(&value), sizeof(T));
  if (!out) throw std::runtime_error("binary output write failed");
}
}
std::uint32_t read_count(std::istream& input) {
  const auto count = read_little<std::uint32_t>(input);
  if (count > 100000) throw std::runtime_error("matrix count exceeds local safety limit");
  return count;
}
Matrix read_matrix(std::istream& input) {
  const auto n = read_little<std::uint32_t>(input);
  if (n < 3 || n > 10000) throw std::runtime_error("N must be within [3, 10000]");
  const std::size_t elements = std::size_t(n) * n;
  Matrix matrix{n, std::vector<double>(elements)};
  input.read(reinterpret_cast<char*>(matrix.values.data()), static_cast<std::streamsize>(elements * sizeof(double)));
  if (!input) throw std::runtime_error("truncated matrix payload");
  return matrix;
}
void write_count(std::ostream& output, std::uint32_t count) { write_little(output, count); }
void write_matrix(std::ostream& output, const Matrix& matrix) {
  if (matrix.values.size() != std::size_t(matrix.n) * matrix.n) throw std::runtime_error("invalid output matrix size");
  write_little(output, matrix.n);
  output.write(reinterpret_cast<const char*>(matrix.values.data()), static_cast<std::streamsize>(matrix.values.size() * sizeof(double)));
  if (!output) throw std::runtime_error("binary output write failed");
}
void ensure_eof(std::istream& input) {
  if (input.peek() != std::char_traits<char>::eof()) throw std::runtime_error("unexpected trailing binary data");
  if (input.bad()) throw std::runtime_error("binary input read failed");
}
}
