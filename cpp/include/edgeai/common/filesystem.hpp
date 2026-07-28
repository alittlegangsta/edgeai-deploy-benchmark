#pragma once

// GCC 7 implements the C++17 filesystem API in the experimental namespace.
// Keep that toolchain-specific detail behind one project alias so newer hosts
// continue to use the standard C++17 implementation.
#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ < 8
#include <experimental/filesystem>
namespace edgeai {
namespace filesystem = std::experimental::filesystem;
}
#else
#include <filesystem>
namespace edgeai {
namespace filesystem = std::filesystem;
}
#endif
