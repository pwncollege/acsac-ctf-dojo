#include <sys/prctl.h>
#include <sys/resource.h>
#include <unistd.h>

#include <boost/algorithm/string.hpp>
#include <boost/asio.hpp>
#include <cassert>

#include "spdlog/spdlog.h"

using boost::asio::ip::tcp;

struct ValueList {
    explicit ValueList() : size_(0), on_get_(nullptr) {
        volatile void* x = (void*) &system;
    }

    ~ValueList() {}

    std::uint32_t add_values(tcp::socket& socket, std::uint32_t num_values) {
        auto new_size = size_ + num_values;
        if (new_size > MAX_VALUES) {
            return size_;
        }

        boost::system::error_code error;
        std::uint64_t checksum;
        boost::asio::read(socket, boost::asio::buffer(&checksum, sizeof(checksum)), error);
        if (error) {
            throw boost::system::system_error(error);
        }
        boost::asio::read(socket, boost::asio::buffer(values_ + size_, num_values * sizeof(*values_)), error);
        if (error) {
            throw boost::system::system_error(error);
        }

        std::uint64_t c = 0;
        for (auto i = size_; i < num_values + size_; ++i) {
            c += values_[i];
        }

        if (c == checksum) {
            size_ = new_size;
        }

        spdlog::info("size_={}", size_);

        return size_;
    }

    std::uint64_t* get_values(std::uint32_t offset, std::uint32_t size) {
        if (offset + size >= size_) {
            return nullptr;
        }
        if (on_get_) {
            return on_get_(&values_[offset], size);
        }
        return &values_[offset];
    }

    std::uint32_t delete_values(std::uint32_t size) {
        if (size > size_) {
            size = size_;
        }
        size_ -= size;
        return size_;
    }

    static const std::size_t MAX_VALUES = 64;

    std::uint64_t values_[MAX_VALUES];
    std::uint32_t size_;
    std::uint64_t* (*on_get_)(std::uint64_t*, std::uint32_t);
};

ValueList values;

std::string process_request(tcp::socket& socket, const tcp::endpoint& remote, const std::uint8_t request_type) {
    boost::system::error_code error;
    std::uint32_t num_values;

    switch (request_type) {
        case 1: {
            boost::asio::read(socket, boost::asio::buffer(&num_values, sizeof(num_values)), error);
            if (error) {
                throw boost::system::system_error(error);
            }

            spdlog::info("[{}:{}] adding {} values", remote.address().to_string(), remote.port(), num_values);
            return std::to_string(values.add_values(socket, num_values));
        }
        case 2: {
            std::string output;
            std::uint32_t offset;
            boost::asio::read(socket, boost::asio::buffer(&offset, sizeof(offset)), error);
            if (error) {
                throw boost::system::system_error(error);
            }
            boost::asio::read(socket, boost::asio::buffer(&num_values, sizeof(num_values)), error);
            if (error) {
                throw boost::system::system_error(error);
            }
            spdlog::info(
                "[{}:{}] getting {} values at {}", remote.address().to_string(), remote.port(), offset, num_values);
            auto ys = values.get_values(offset, num_values);
            if (ys) {
                for (auto i = 0u; i < num_values; ++i) {
                    output += std::to_string(ys[i]) + ",";
                }
            }
            return output;
        }
        case 3: {
            boost::asio::read(socket, boost::asio::buffer(&num_values, sizeof(num_values)), error);
            if (error) {
                throw boost::system::system_error(error);
            }
            spdlog::info("[{}:{}] deleting {} values", remote.address().to_string(), remote.port(), num_values);
            return std::to_string(values.delete_values(num_values));
        }
        default:
            return {};
    }
}

void on_client(tcp::socket socket) {
    const auto remote = socket.remote_endpoint();
    spdlog::info("[{}:{}] processing client request", remote.address().to_string(), remote.port());

    try {
        std::uint8_t request_type;
        boost::system::error_code error;
        boost::asio::read(socket, boost::asio::buffer(&request_type, sizeof(request_type)), error);
        if (error) {
            throw boost::system::system_error(error);
        }

        const auto response = process_request(socket, remote, request_type);
        const std::uint16_t size = response.size();
        boost::asio::write(socket, boost::asio::buffer(&size, sizeof(size)));
        boost::asio::write(socket, boost::asio::buffer(response));
    } catch (const std::exception& e) {
        spdlog::error("[{}:{}] {}", remote.address().to_string(), remote.port(), e.what());
    }
}

[[noreturn]] void execute_server(boost::asio::io_context& context, std::uint16_t port) {
    tcp::acceptor acceptor(context, {tcp::v4(), port});
    while (true) {
        std::thread(on_client, acceptor.accept()).detach();
    }
}

int main(int argc, char* argv[]) {
    try {
        if (argc < 2) {
            throw std::runtime_error(fmt::format("usage: {} <port>", argv[0]));
        }

        const auto port = std::strtoul(argv[1], nullptr, 10);
        boost::asio::io_context context(1);
        execute_server(context, port);
    } catch (const std::exception& e) {
        spdlog::error("{}", e.what());
        return 1;
    }
}
