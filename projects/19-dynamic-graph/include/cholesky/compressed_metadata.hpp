#pragma once
#include <optional>
#include <string>
#include <string_view>
namespace chol {
// A wrapper around complete Metadata, not a new inner execution schema.
std::string decode_metadata_container(std::string_view bytes);
std::optional<std::string> read_compressed_metadata(const std::string& path);
}
