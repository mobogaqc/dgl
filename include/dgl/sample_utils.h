/*!
 *  Copyright (c) 2019 by Contributors
 * \file dgl/sample_utils.h
 * \brief Sampling utilities
 */
#ifndef DGL_SAMPLE_UTILS_H_
#define DGL_SAMPLE_UTILS_H_

#include <algorithm>
#include <utility>
#include <queue>
#include <cstdlib>
#include <cmath>
#include <numeric>
#include <limits>
#include <vector>
#include "random.h"

namespace dgl {
namespace utils {

template <
  typename Idx,
  typename DType,
  bool replace>
class BaseSampler {
 public:
  virtual Idx Draw() {
    LOG(INFO) << "Not implemented yet.";
    return 0;
  }
};

/*
 * AliasSampler is used to sample elements from a given discrete categorical distribution.
 * Algorithm: Alias Method(https://en.wikipedia.org/wiki/Alias_method)
 * Sampler building complexity: O(n)
 * Sample w/ replacement complexity: O(1)
 * Sample w/o replacement complexity: O(log n)
 */
template <
  typename Idx,
  typename DType,
  bool replace>
class AliasSampler: public BaseSampler<Idx, DType, replace> {
 private:
  RandomEngine *re;
  Idx N;
  DType accum, taken;             // accumulated likelihood
  std::vector<Idx> K;             // alias table
  std::vector<DType> U;           // probability table
  std::vector<DType> _prob;       // category distribution
  std::vector<bool> used;         // indicate availability, activated when replace=false;
  std::vector<Idx> id_mapping;    // index mapping, activated when replace=false;

  inline Idx Map(Idx x) const {   // Map consecutive indices to unused elements
    if (replace)
      return x;
    else
      return id_mapping[x];
  }

  void Reconstruct(const std::vector<DType>& prob) {  // Reconstruct alias table
    N = 0;
    accum = 0.;
    taken = 0.;
    if (!replace)
      id_mapping.clear();
    for (Idx i = 0; i < prob.size(); ++i)
      if (!used[i]) {
        N++;
        accum += prob[i];
        if (!replace)
          id_mapping.push_back(i);
      }
    if (N == 0) LOG(FATAL) << "Cannot take more sample than population when 'replace=false'";
    K.resize(N);
    U.resize(N);
    DType avg = accum / static_cast<DType>(N);
    std::fill(U.begin(), U.end(), avg);     // initialize U
    std::queue<std::pair<Idx, DType> > under, over;
    for (Idx i = 0; i < N; ++i) {
      DType p = prob[Map(i)];
      if (p > avg)
        over.push(std::make_pair(i, p));
      else
        under.push(std::make_pair(i, p));
      K[i] = i;                             // initialize K
    }
    while (!under.empty() && !over.empty()) {
      auto u_pair = under.front(), o_pair = over.front();
      Idx i_u = u_pair.first, i_o = o_pair.first;
      DType p_u = u_pair.second, p_o = o_pair.second;
      K[i_u] = i_o;
      U[i_u] = p_u;
      if (p_o + p_u > 2 * avg)
        over.push(std::make_pair(i_o, p_o + p_u - avg));
      else if (p_o + p_u < 2 * avg)
        under.push(std::make_pair(i_o, p_o + p_u - avg));
      under.pop();
      over.pop();
    }
  }

 public:
  void ResetState(const std::vector<DType>& prob) {
    used.resize(prob.size());
    if (!replace)
      _prob = prob;
    std::fill(used.begin(), used.end(), false);
    Reconstruct(prob);
  }

  explicit AliasSampler(RandomEngine* re, const std::vector<DType>& prob): re(re) {
    ResetState(prob);
  }

  ~AliasSampler() {}

  Idx Draw() {
    DType avg = accum / N;
    if (!replace) {
      if (2 * taken >= accum)
        Reconstruct(_prob);
      while (true) {
        DType dice = re->Uniform<DType>(0, N);
        Idx i = static_cast<Idx>(dice), rst;
        DType p = (dice - i) * avg;
        if (p <= U[Map(i)]) {
          rst = Map(i);
        } else {
          rst = Map(K[i]);
        }
        DType cap = _prob[rst];
        if (!used[rst]) {
          used[rst] = true;
          taken += cap;
          return rst;
        }
      }
    }
    DType dice = re->Uniform<DType>(0, N);
    Idx i = static_cast<Idx>(dice);
    DType p = (dice - i) * avg;
    if (p <= U[Map(i)])
        return Map(i);
    else
        return Map(K[i]);
  }
};


/*
 * CDFSampler is used to sample elements from a given discrete categorical distribution.
 * Algorithm: create a cumulative distribution function and conduct binary search for sampling.
 * Reference: https://github.com/numpy/numpy/blob/d37908/numpy/random/mtrand.pyx#L804
 * Sampler building complexity: O(n)
 * Sample w/ and w/o replacement complexity: O(log n)
 */
template <
  typename Idx,
  typename DType,
  bool replace>
class CDFSampler: public BaseSampler<Idx, DType, replace> {
 private:
  RandomEngine *re;
  Idx N;
  DType accum, taken;
  std::vector<DType> _prob;     // categorical distribution
  std::vector<DType> cdf;       // cumulative distribution function
  std::vector<bool> used;       // indicate availability, activated when replace=false;
  std::vector<Idx> id_mapping;  // indicate index mapping, activated when replace=false;

  inline Idx Map(Idx x) const {   // Map consecutive indices to unused elements
    if (replace)
      return x;
    else
      return id_mapping[x];
  }

  void Reconstruct(const std::vector<DType>& prob) {  // Reconstruct CDF
    N = 0;
    accum = 0.;
    taken = 0.;
    if (!replace)
      id_mapping.clear();
    cdf.clear();
    cdf.push_back(0);
    for (Idx i = 0; i < prob.size(); ++i)
      if (!used[i]) {
        N++;
        accum += prob[i];
        if (!replace)
          id_mapping.push_back(i);
        cdf.push_back(accum);
      }
    if (N == 0) LOG(FATAL) << "Cannot take more sample than population when 'replace=false'";
  }

 public:
  void ResetState(const std::vector<DType>& prob) {
    used.resize(prob.size());
    if (!replace)
      _prob = prob;
    std::fill(used.begin(), used.end(), false);
    Reconstruct(prob);
  }

  explicit CDFSampler(RandomEngine *re, const std::vector<DType>& prob): re(re) {
    ResetState(prob);
  }

  ~CDFSampler() {}

  Idx Draw() {
    DType eps = std::numeric_limits<DType>::min();
    if (!replace) {
      if (2 * taken >= accum)
        Reconstruct(_prob);
      while (true) {
        DType p = std::max(re->Uniform<DType>(0., accum), eps);
        Idx rst = Map(std::lower_bound(cdf.begin(), cdf.end(), p) - cdf.begin() - 1);
        DType cap = _prob[rst];
        if (!used[rst]) {
          used[rst] = true;
          taken += cap;
          return rst;
        }
      }
    }
    DType p = std::max(re->Uniform<DType>(0., accum), eps);
    return Map(std::lower_bound(cdf.begin(), cdf.end(), p) - cdf.begin() - 1);
  }
};


/*
 * TreeSampler is used to sample elements from a given discrete categorical distribution.
 * Algorithm: create a heap that stores accumulated likelihood of its leaf descendents.
 * Reference: https://blog.smola.org/post/1016514759
 * Sampler building complexity: O(n)
 * Sample w/ and w/o replacement complexity: O(log n)
 */
template <
  typename Idx,
  typename DType,
  bool replace>
class TreeSampler: public BaseSampler<Idx, DType, replace> {
 private:
  RandomEngine *re;
  std::vector<DType> weight;    // accumulated likelihood of subtrees.
  int64_t N, num_leafs;

 public:
  void ResetState(const std::vector<DType>& prob) {
    std::fill(weight.begin(), weight.end(), 0);
    for (int i = 0; i < prob.size(); ++i)
      weight[num_leafs + i] = prob[i];
    for (int i = num_leafs - 1; i >= 1; --i)
      weight[i] = weight[i * 2] + weight[i * 2 + 1];
  }

  explicit TreeSampler(RandomEngine *re, const std::vector<DType>& prob): re(re) {
    num_leafs = 1;
    while (num_leafs < prob.size())
      num_leafs *= 2;
    N = num_leafs * 2;
    weight.resize(N);
    ResetState(prob);
  }

  Idx Draw() {
    int64_t cur = 1;
    DType p = re->Uniform<DType>(0, weight[cur]);
    DType accum = 0.;
    while (cur < num_leafs) {
      DType w_l = weight[cur * 2], w_r = weight[cur * 2 + 1];
      DType pivot = accum + w_l;
      // w_r > 0 can depress some numerical problems.
      Idx shift = static_cast<Idx>(p > pivot && w_r > 0);
      cur = cur * 2 + shift;
      if (shift == 1)
        accum = pivot;
    }
    Idx rst = cur - num_leafs;
    if (!replace) {
      while (cur >= 1) {
        if (cur >= num_leafs)
          weight[cur] = 0.;
        else
          weight[cur] = weight[cur * 2] + weight[cur * 2 + 1];
        cur /= 2;
      }
    }
    return rst;
  }
};

};  // namespace utils
};  // namespace dgl

#endif  // DGL_SAMPLE_UTILS_H_
