#include "cholesky/runtime.hpp"
#include <cmath>
#include <cstring>
#include <iostream>
#include <sstream>
#include <stdexcept>
extern "C" int cholesky_reference(const double* a, double* l, int n);

void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
int main() {
  try {
    const chol::Metadata metadata{"cholesky_column_v1", "fp64_ascending_k_no_fma", "column_barrier_diagonal_then_rows"};
    chol::Matrix a{3, {4, 2, 2, 2, 10, 4, 2, 4, 9}};
    const auto l = chol::execute(a, metadata);
    require(l.values[0] == 2 && l.values[3] == 1 && l.values[4] == 3 && l.values[6] == 1 && l.values[7] == 1, "known factor incorrect");
    for (std::size_t i = 0; i < 3; ++i) for (std::size_t j = 0; j < 3; ++j) {
      double reconstructed = 0;
      for (std::size_t k = 0; k < 3; ++k) reconstructed += l.values[i*3+k]*l.values[j*3+k];
      require(std::abs(reconstructed - a.values[i*3+j]) < 1e-12, "LL^T residual too high");
    }
    chol::Matrix large{67, std::vector<double>(67*67)};
    for (std::size_t i = 0; i < 67; ++i) for (std::size_t j = 0; j < 67; ++j) large.values[i*67+j] = i == j ? 70.0 : 0.125;
    const auto serial = chol::execute(large, metadata);
    const auto parallel = chol::execute(large, metadata, {true, 4});
    std::vector<double> reference(large.values.size(), 0.0);
    cholesky_reference(large.values.data(), reference.data(), static_cast<int>(large.n));
    require(std::memcmp(serial.values.data(), reference.data(), reference.size()*sizeof(double)) == 0, "runtime differs from self-built C reference bits");
    require(std::memcmp(serial.values.data(), parallel.values.data(), serial.values.size()*sizeof(double)) == 0, "parallel changed arithmetic bits");
    std::stringstream binary(std::ios::in | std::ios::out | std::ios::binary);
    chol::write_count(binary, 1); chol::write_matrix(binary, a);
    binary.seekg(0); require(chol::read_count(binary) == 1, "count round trip failed");
    const auto restored = chol::read_matrix(binary);
    require(restored.values == a.values && restored.n == 3, "binary round trip failed");
    chol::ensure_eof(binary);
    bool rejected = false;
    std::stringstream short_input(std::string(2, '\0')); try { chol::read_count(short_input); } catch (...) { rejected = true; }
    require(rejected, "truncated input accepted");
    a.values[0] = -1; rejected = false;
    try { chol::execute(a, metadata); } catch (...) { rejected = true; }
    require(rejected, "non-SPD accepted");
    std::cout << "known factor, residual, serial/parallel byte equivalence, binary IO and invalid input passed\n";
    return 0;
  } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
