/*!
 *  Copyright (c) 2018 by Contributors
 * \file graph/sampler.cc
 * \brief DGL sampler implementation
 */

#include <dgl/sampler.h>
#include <dmlc/omp.h>
#include <dgl/immutable_graph.h>
#include <algorithm>
#include <cstdlib>
#include <cmath>

#ifdef _MSC_VER
// rand in MS compiler works well in multi-threading.
int rand_r(unsigned *seed) {
  return rand();
}
#endif

namespace dgl {

namespace {

/*
 * ArrayHeap is used to sample elements from vector
 */
class ArrayHeap {
 public:
  explicit ArrayHeap(const std::vector<float>& prob) {
    vec_size_ = prob.size();
    bit_len_ = ceil(log2(vec_size_));
    limit_ = 1 << bit_len_;
    // allocate twice the size
    heap_.resize(limit_ << 1, 0);
    // allocate the leaves
    for (int i = limit_; i < vec_size_+limit_; ++i) {
      heap_[i] = prob[i-limit_];
    }
    // iterate up the tree (this is O(m))
    for (int i = bit_len_-1; i >= 0; --i) {
      for (int j = (1 << i); j < (1 << (i + 1)); ++j) {
        heap_[j] = heap_[j << 1] + heap_[(j << 1) + 1];
      }
    }
  }
  ~ArrayHeap() {}

  /*
   * Remove term from index (this costs O(log m) steps)
   */
  void Delete(size_t index) {
    size_t i = index + limit_;
    float w = heap_[i];
    for (int j = bit_len_; j >= 0; --j) {
      heap_[i] -= w;
      i = i >> 1;
    }
  }

  /*
   * Add value w to index (this costs O(log m) steps)
   */
  void Add(size_t index, float w) {
    size_t i = index + limit_;
    for (int j = bit_len_; j >= 0; --j) {
      heap_[i] += w;
      i = i >> 1;
    }
  }

  /*
   * Sample from arrayHeap
   */
  size_t Sample(unsigned int* seed) {
    float xi = heap_[1] * (rand_r(seed)%100/101.0);
    int i = 1;
    while (i < limit_) {
      i = i << 1;
      if (xi >= heap_[i]) {
        xi -= heap_[i];
        i += 1;
      }
    }
    return i - limit_;
  }

  /*
   * Sample a vector by given the size n
   */
  void SampleWithoutReplacement(size_t n, std::vector<size_t>* samples, unsigned int* seed) {
    // sample n elements
    for (size_t i = 0; i < n; ++i) {
      samples->at(i) = this->Sample(seed);
      this->Delete(samples->at(i));
    }
  }

 private:
  int vec_size_;  // sample size
  int bit_len_;   // bit size
  int limit_;
  std::vector<float> heap_;
};

/*
 * Uniformly sample integers from [0, set_size) without replacement.
 */
void RandomSample(size_t set_size, size_t num, std::vector<size_t>* out, unsigned int* seed) {
  std::unordered_set<size_t> sampled_idxs;
  while (sampled_idxs.size() < num) {
    sampled_idxs.insert(rand_r(seed) % set_size);
  }
  out->clear();
  out->insert(out->end(), sampled_idxs.begin(), sampled_idxs.end());
}

/*
 * For a sparse array whose non-zeros are represented by nz_idxs,
 * negate the sparse array and outputs the non-zeros in the negated array.
 */
void NegateArray(const std::vector<size_t> &nz_idxs,
                 size_t arr_size,
                 std::vector<size_t>* out) {
  // nz_idxs must have been sorted.
  auto it = nz_idxs.begin();
  size_t i = 0;
  CHECK_GT(arr_size, nz_idxs.back());
  for (; i < arr_size && it != nz_idxs.end(); i++) {
    if (*it == i) {
      it++;
      continue;
    }
    out->push_back(i);
  }
  for (; i < arr_size; i++) {
    out->push_back(i);
  }
}

/*
 * Uniform sample vertices from a list of vertices.
 */
void GetUniformSample(const dgl_id_t* edge_id_list,
                      const dgl_id_t* vid_list,
                      const size_t ver_len,
                      const size_t max_num_neighbor,
                      std::vector<dgl_id_t>* out_ver,
                      std::vector<dgl_id_t>* out_edge,
                      unsigned int* seed) {
  // Copy vid_list to output
  if (ver_len <= max_num_neighbor) {
    out_ver->insert(out_ver->end(), vid_list, vid_list + ver_len);
    out_edge->insert(out_edge->end(), edge_id_list, edge_id_list + ver_len);
    return;
  }
  // If we just sample a small number of elements from a large neighbor list.
  std::vector<size_t> sorted_idxs;
  if (ver_len > max_num_neighbor * 2) {
    sorted_idxs.reserve(max_num_neighbor);
    RandomSample(ver_len, max_num_neighbor, &sorted_idxs, seed);
    std::sort(sorted_idxs.begin(), sorted_idxs.end());
  } else {
    std::vector<size_t> negate;
    negate.reserve(ver_len - max_num_neighbor);
    RandomSample(ver_len, ver_len - max_num_neighbor,
                 &negate, seed);
    std::sort(negate.begin(), negate.end());
    NegateArray(negate, ver_len, &sorted_idxs);
  }
  // verify the result.
  CHECK_EQ(sorted_idxs.size(), max_num_neighbor);
  for (size_t i = 1; i < sorted_idxs.size(); i++) {
    CHECK_GT(sorted_idxs[i], sorted_idxs[i - 1]);
  }
  for (auto idx : sorted_idxs) {
    out_ver->push_back(vid_list[idx]);
    out_edge->push_back(edge_id_list[idx]);
  }
}

/*
 * Non-uniform sample via ArrayHeap
 */
void GetNonUniformSample(const float* probability,
                         const dgl_id_t* edge_id_list,
                         const dgl_id_t* vid_list,
                         const size_t ver_len,
                         const size_t max_num_neighbor,
                         std::vector<dgl_id_t>* out_ver,
                         std::vector<dgl_id_t>* out_edge,
                         unsigned int* seed) {
  // Copy vid_list to output
  if (ver_len <= max_num_neighbor) {
    out_ver->insert(out_ver->end(), vid_list, vid_list + ver_len);
    out_edge->insert(out_edge->end(), edge_id_list, edge_id_list + ver_len);
    return;
  }
  // Make sample
  std::vector<size_t> sp_index(max_num_neighbor);
  std::vector<float> sp_prob(ver_len);
  for (size_t i = 0; i < ver_len; ++i) {
    sp_prob[i] = probability[vid_list[i]];
  }
  ArrayHeap arrayHeap(sp_prob);
  arrayHeap.SampleWithoutReplacement(max_num_neighbor, &sp_index, seed);
  out_ver->resize(max_num_neighbor);
  out_edge->resize(max_num_neighbor);
  for (size_t i = 0; i < max_num_neighbor; ++i) {
    size_t idx = sp_index[i];
    out_ver->at(i) = vid_list[idx];
    out_edge->at(i) = edge_id_list[idx];
  }
  sort(out_ver->begin(), out_ver->end());
  sort(out_edge->begin(), out_edge->end());
}

/*
 * Used for subgraph sampling
 */
struct neigh_list {
  std::vector<dgl_id_t> neighs;
  std::vector<dgl_id_t> edges;
  neigh_list(const std::vector<dgl_id_t> &_neighs,
             const std::vector<dgl_id_t> &_edges)
    : neighs(_neighs), edges(_edges) {}
};

struct neighbor_info {
  dgl_id_t id;
  size_t pos;
  size_t num_edges;

  neighbor_info(dgl_id_t id, size_t pos, size_t num_edges) {
    this->id = id;
    this->pos = pos;
    this->num_edges = num_edges;
  }
};

NodeFlow ConstructNodeFlow(std::vector<dgl_id_t> neighbor_list,
                           std::vector<dgl_id_t> edge_list,
                           std::vector<size_t> layer_offsets,
                           std::vector<std::pair<dgl_id_t, int> > *sub_vers,
                           std::vector<neighbor_info> *neigh_pos,
                           const std::string &edge_type,
                           int64_t num_edges, int num_hops, bool is_multigraph) {
  NodeFlow nf;
  uint64_t num_vertices = sub_vers->size();
  nf.node_mapping = IdArray::Empty({static_cast<int64_t>(num_vertices)},
                                   DLDataType{kDLInt, 64, 1}, DLContext{kDLCPU, 0});
  nf.edge_mapping = IdArray::Empty({static_cast<int64_t>(num_edges)},
                                   DLDataType{kDLInt, 64, 1}, DLContext{kDLCPU, 0});
  nf.layer_offsets = IdArray::Empty({static_cast<int64_t>(num_hops + 1)},
                                    DLDataType{kDLInt, 64, 1}, DLContext{kDLCPU, 0});
  nf.flow_offsets = IdArray::Empty({static_cast<int64_t>(num_hops)},
                                    DLDataType{kDLInt, 64, 1}, DLContext{kDLCPU, 0});

  dgl_id_t *node_map_data = static_cast<dgl_id_t *>(nf.node_mapping->data);
  dgl_id_t *layer_off_data = static_cast<dgl_id_t *>(nf.layer_offsets->data);
  dgl_id_t *flow_off_data = static_cast<dgl_id_t *>(nf.flow_offsets->data);
  dgl_id_t *edge_map_data = static_cast<dgl_id_t *>(nf.edge_mapping->data);

  // Construct sub_csr_graph
  auto subg_csr = std::make_shared<ImmutableGraph::CSR>(num_vertices, num_edges);
  subg_csr->indices.resize(num_edges);
  subg_csr->edge_ids.resize(num_edges);
  dgl_id_t* col_list_out = subg_csr->indices.data();
  int64_t* indptr_out = subg_csr->indptr.data();
  size_t collected_nedges = 0;

  // The data from the previous steps:
  // * node data: sub_vers (vid, layer), neigh_pos,
  // * edge data: neighbor_list, edge_list, probability.
  // * layer_offsets: the offset in sub_vers.
  dgl_id_t ver_id = 0;
  std::vector<std::unordered_map<dgl_id_t, dgl_id_t>> layer_ver_maps;
  layer_ver_maps.resize(num_hops);
  size_t out_node_idx = 0;
  for (int layer_id = num_hops - 1; layer_id >= 0; layer_id--) {
    // We sort the vertices in a layer so that we don't need to sort the neighbor Ids
    // after remap to a subgraph.
    std::sort(sub_vers->begin() + layer_offsets[layer_id],
              sub_vers->begin() + layer_offsets[layer_id + 1],
              [](const std::pair<dgl_id_t, dgl_id_t> &a1,
                 const std::pair<dgl_id_t, dgl_id_t> &a2) {
      return a1.first < a2.first;
    });

    // Save the sampled vertices and its layer Id.
    for (size_t i = layer_offsets[layer_id]; i < layer_offsets[layer_id + 1]; i++) {
      node_map_data[out_node_idx++] = sub_vers->at(i).first;
      layer_ver_maps[layer_id].insert(std::pair<dgl_id_t, dgl_id_t>(sub_vers->at(i).first,
                                                                    ver_id++));
      CHECK_EQ(sub_vers->at(i).second, layer_id);
    }
  }
  CHECK(out_node_idx == num_vertices);

  // sampling algorithms have to start from the seed nodes, so the seed nodes are
  // in the first layer and the input nodes are in the last layer.
  // When we expose the sampled graph to a Python user, we say the input nodes
  // are in the first layer and the seed nodes are in the last layer.
  // Thus, when we copy sampled results to a CSR, we need to reverse the order of layers.
  size_t row_idx = 0;
  for (size_t i = layer_offsets[num_hops - 1]; i < layer_offsets[num_hops]; i++) {
    indptr_out[row_idx++] = 0;
  }
  layer_off_data[0] = 0;
  layer_off_data[1] = layer_offsets[num_hops] - layer_offsets[num_hops - 1];
  int out_layer_idx = 1;
  for (int layer_id = num_hops - 2; layer_id >= 0; layer_id--) {
    std::sort(neigh_pos->begin() + layer_offsets[layer_id],
              neigh_pos->begin() + layer_offsets[layer_id + 1],
              [](const neighbor_info &a1, const neighbor_info &a2) {
                return a1.id < a2.id;
              });

    for (size_t i = layer_offsets[layer_id]; i < layer_offsets[layer_id + 1]; i++) {
      dgl_id_t dst_id = sub_vers->at(i).first;
      CHECK_EQ(dst_id, neigh_pos->at(i).id);
      size_t pos = neigh_pos->at(i).pos;
      CHECK_LE(pos, neighbor_list.size());
      size_t num_edges = neigh_pos->at(i).num_edges;
      if (neighbor_list.empty()) CHECK_EQ(num_edges, 0);

      // We need to map the Ids of the neighbors to the subgraph.
      auto neigh_it = neighbor_list.begin() + pos;
      for (size_t i = 0; i < num_edges; i++) {
        dgl_id_t neigh = *(neigh_it + i);
        CHECK(layer_ver_maps[layer_id + 1].find(neigh) != layer_ver_maps[layer_id + 1].end());
        col_list_out[collected_nedges + i] = layer_ver_maps[layer_id + 1][neigh];
      }
      // We can simply copy the edge Ids.
      std::copy_n(edge_list.begin() + pos,
                  num_edges, edge_map_data + collected_nedges);
      collected_nedges += num_edges;
      indptr_out[row_idx+1] = indptr_out[row_idx] + num_edges;
      row_idx++;
    }
    layer_off_data[out_layer_idx + 1] = layer_off_data[out_layer_idx]
        + layer_offsets[layer_id + 1] - layer_offsets[layer_id];
    out_layer_idx++;
  }
  CHECK(row_idx == num_vertices);
  CHECK(indptr_out[row_idx] == num_edges);
  CHECK(out_layer_idx == num_hops);
  CHECK(layer_off_data[out_layer_idx] == num_vertices);

  // Copy flow offsets.
  flow_off_data[0] = 0;
  int out_flow_idx = 0;
  for (size_t i = 0; i < layer_offsets.size() - 2; i++) {
    size_t num_edges = subg_csr->GetDegree(layer_off_data[i + 1], layer_off_data[i + 2]);
    flow_off_data[out_flow_idx + 1] = flow_off_data[out_flow_idx] + num_edges;
    out_flow_idx++;
  }
  CHECK(out_flow_idx == num_hops - 1);
  CHECK(flow_off_data[num_hops - 1] == static_cast<uint64_t>(num_edges));

  for (size_t i = 0; i < subg_csr->edge_ids.size(); i++) {
    subg_csr->edge_ids[i] = i;
  }

  if (edge_type == "in") {
    nf.graph = GraphPtr(new ImmutableGraph(subg_csr, nullptr, is_multigraph));
  } else {
    nf.graph = GraphPtr(new ImmutableGraph(nullptr, subg_csr, is_multigraph));
  }

  return nf;
}

NodeFlow SampleSubgraph(const ImmutableGraph *graph,
                        IdArray seed_arr,
                        const float* probability,
                        const std::string &edge_type,
                        int num_hops,
                        size_t num_neighbor) {
  unsigned int time_seed = time(nullptr);
  size_t num_seeds = seed_arr->shape[0];
  auto orig_csr = edge_type == "in" ? graph->GetInCSR() : graph->GetOutCSR();
  const dgl_id_t* val_list = orig_csr->edge_ids.data();
  const dgl_id_t* col_list = orig_csr->indices.data();
  const int64_t* indptr = orig_csr->indptr.data();
  const dgl_id_t* seed = static_cast<dgl_id_t*>(seed_arr->data);

  std::unordered_set<dgl_id_t> sub_ver_map;  // The vertex Ids in a layer.
  std::vector<std::pair<dgl_id_t, int> > sub_vers;
  sub_vers.reserve(num_seeds * 10);
  // add seed vertices
  for (size_t i = 0; i < num_seeds; ++i) {
    auto ret = sub_ver_map.insert(seed[i]);
    // If the vertex is inserted successfully.
    if (ret.second) {
      sub_vers.emplace_back(seed[i], 0);
    }
  }
  std::vector<dgl_id_t> tmp_sampled_src_list;
  std::vector<dgl_id_t> tmp_sampled_edge_list;
  // ver_id, position
  std::vector<neighbor_info> neigh_pos;
  neigh_pos.reserve(num_seeds);
  std::vector<dgl_id_t> neighbor_list;
  std::vector<dgl_id_t> edge_list;
  std::vector<size_t> layer_offsets(num_hops + 1);
  int64_t num_edges = 0;

  layer_offsets[0] = 0;
  layer_offsets[1] = sub_vers.size();
  for (int layer_id = 1; layer_id < num_hops; layer_id++) {
    // We need to avoid resampling the same node in a layer, but we allow a node
    // to be resampled in multiple layers. We use `sub_ver_map` to keep track of
    // sampled nodes in a layer, and clear it when entering a new layer.
    sub_ver_map.clear();
    // Previous iteration collects all nodes in sub_vers, which are collected
    // in the previous layer. sub_vers is used both as a node collection and a queue.
    for (size_t idx = layer_offsets[layer_id - 1]; idx < layer_offsets[layer_id]; idx++) {
      dgl_id_t dst_id = sub_vers[idx].first;
      const int cur_node_level = sub_vers[idx].second;

      tmp_sampled_src_list.clear();
      tmp_sampled_edge_list.clear();
      dgl_id_t ver_len = *(indptr+dst_id+1) - *(indptr+dst_id);
      if (probability == nullptr) {  // uniform-sample
        GetUniformSample(val_list + *(indptr + dst_id),
                         col_list + *(indptr + dst_id),
                         ver_len,
                         num_neighbor,
                         &tmp_sampled_src_list,
                         &tmp_sampled_edge_list,
                         &time_seed);
      } else {  // non-uniform-sample
        GetNonUniformSample(probability,
                            val_list + *(indptr + dst_id),
                            col_list + *(indptr + dst_id),
                            ver_len,
                            num_neighbor,
                            &tmp_sampled_src_list,
                            &tmp_sampled_edge_list,
                            &time_seed);
      }
      CHECK_EQ(tmp_sampled_src_list.size(), tmp_sampled_edge_list.size());
      neigh_pos.emplace_back(dst_id, neighbor_list.size(), tmp_sampled_src_list.size());
      // Then push the vertices
      for (size_t i = 0; i < tmp_sampled_src_list.size(); ++i) {
        neighbor_list.push_back(tmp_sampled_src_list[i]);
      }
      // Finally we push the edge list
      for (size_t i = 0; i < tmp_sampled_edge_list.size(); ++i) {
        edge_list.push_back(tmp_sampled_edge_list[i]);
      }
      num_edges += tmp_sampled_src_list.size();
      for (size_t i = 0; i < tmp_sampled_src_list.size(); ++i) {
        // We need to add the neighbor in the hashtable here. This ensures that
        // the vertex in the queue is unique. If we see a vertex before, we don't
        // need to add it to the queue again.
        auto ret = sub_ver_map.insert(tmp_sampled_src_list[i]);
        // If the sampled neighbor is inserted to the map successfully.
        if (ret.second) {
          sub_vers.emplace_back(tmp_sampled_src_list[i], cur_node_level + 1);
        }
      }
    }
    layer_offsets[layer_id + 1] = layer_offsets[layer_id] + sub_ver_map.size();
    CHECK_EQ(layer_offsets[layer_id + 1], sub_vers.size());
  }

  return ConstructNodeFlow(neighbor_list, edge_list, layer_offsets, &sub_vers, &neigh_pos,
                           edge_type, num_edges, num_hops, graph->IsMultigraph());
}

}  // namespace

NodeFlow SamplerOp::NeighborUniformSample(const ImmutableGraph *graph, IdArray seeds,
                                          const std::string &edge_type,
                                          int num_hops, int expand_factor) {
  return SampleSubgraph(graph,
                        seeds,                 // seed vector
                        nullptr,               // sample_id_probability
                        edge_type,
                        num_hops + 1,
                        expand_factor);
}

IdArray SamplerOp::RandomWalk(
    const GraphInterface *gptr,
    IdArray seeds,
    int num_traces,
    int num_hops) {
  const int num_nodes = seeds->shape[0];
  const dgl_id_t *seed_ids = static_cast<dgl_id_t *>(seeds->data);
  IdArray traces = IdArray::Empty(
      {num_nodes, num_traces, num_hops + 1},
      DLDataType{kDLInt, 64, 1},
      DLContext{kDLCPU, 0});
  dgl_id_t *trace_data = static_cast<dgl_id_t *>(traces->data);

#pragma omp parallel
  {
    // get per-thread seed
    unsigned int random_seed = time(nullptr) ^ omp_get_thread_num();

#pragma omp for
    for (int i = 0; i < num_nodes; ++i) {
      const dgl_id_t seed_id = seed_ids[i];

      for (int j = 0; j < num_traces; ++j) {
        dgl_id_t cur = seed_id;
        const int kmax = num_hops + 1;

        for (int k = 0; k < kmax; ++k) {
          const size_t offset = ((size_t)i * num_traces + j) * kmax + k;
          trace_data[offset] = cur;

          const auto succ = gptr->SuccVec(cur);
          const size_t size = succ.size();
          cur = succ[rand_r(&random_seed) % size];
        }
      }
    }
  }

  return traces;
}

}  // namespace dgl
