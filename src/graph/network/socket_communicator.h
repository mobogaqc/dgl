/*!
 *  Copyright (c) 2019 by Contributors
 * \file communicator.h
 * \brief SocketCommunicator for DGL distributed training.
 */
#ifndef DGL_GRAPH_NETWORK_SOCKET_COMMUNICATOR_H_
#define DGL_GRAPH_NETWORK_SOCKET_COMMUNICATOR_H_

#include <thread>
#include <vector>
#include <string>

#include "communicator.h"
#include "msg_queue.h"
#include "tcp_socket.h"

namespace dgl {
namespace network {

using dgl::network::MessageQueue;
using dgl::network::TCPSocket;

/*!
 * \brief Implementation of Communicator class with TCP socket.
 */
class SocketCommunicator : public Communicator {
 public:
  /*!
   * \brief Initialize Communicator
   * \param is_sender true for sender and false for receiver
   * \param ip ip address
   * \param port end port
   * (e.g. "168.123.2.43:50051"). For Receiver, this address identifies
   * the local listening endpoint (e.g. "0.0.0.0:50051").
   * \param num_sender number of senders, only used for receiver.
   * \param queue_size the size of message queue, only for receiver.
   * \return true for success and false for error
   */
  bool Initialize(bool is_sender,
                  const char* ip,
                  int port,
                  int num_sender = 1,
                  int64_t queue_size = 5 * 1024 * 1024);
  /*!
   * \brief Send message to receiver node
   * \param src data pointer
   * \param size data size
   * \return bytes send
   *   > 0 : bytes send
   *   - 1 : error
   */
  int64_t Send(char* src, int64_t size);

  /*!
   * \brief Receive mesesage from sender node, we
   * actually reading data from local message queue.
   * \param dest destination data pointer
   * \param max_size maximal data size
   * \return bytes received
   *   > 0 : bytes received
   *   - 1 : error
   */
  int64_t Receive(char* dest, int64_t max_size);

  /*!
   * \brief Finalize the SocketCommunicator class
   */
  void Finalize();

 private:
  /*!
   * \brief Is a sender or reciever node?
   */
  bool is_sender_;

  /*!
   * \brief number of sender
   */
  int num_sender_;

  /*!
   * \brief maximal size of message queue
   */ 
  int64_t queue_size_;

  /*!
   * \brief socket list
   */ 
  std::vector<TCPSocket*> socket_;

  /*!
   * \brief Thread pool for socket connection
   */ 
  std::vector<std::thread*> thread_;

  /*!
   * \brief Message queue for communicator
   */ 
  MessageQueue* queue_;

  /*!
   * \brief Initalize sender node
   * \param ip receiver ip address
   * \param port receiver port
   * \return true for success and false for error
   */ 
  bool InitSender(const char* ip, int port);

  /*!
   * \brief Initialize receiver node
   * \param ip receiver ip address
   * \param port receiver port
   * \param num_sender number of sender
   * \param queue_size size of message queue
   * \return true for success and false for error
   */ 
  bool InitReceiver(const char* ip,
                    int port,
                    int num_sender,
                    int64_t queue_size);

  /*!
   * \brief Finalize sender node
   */ 
  void FinalizeSender();

  /*!
   * \brief Finalize receiver node
   */ 
  void FinalizeReceiver();

  /*!
   * \brief Process received message in independent threads
   * \param socket new accpeted socket
   * \param queue message queue
   */ 
  static void MsgHandler(TCPSocket* socket, MessageQueue* queue);
};

}  // namespace network
}  // namespace dgl

#endif  // DGL_GRAPH_NETWORK_SOCKET_COMMUNICATOR_H_
