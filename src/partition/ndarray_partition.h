/*!
 *  Copyright (c) 2021 by Contributors
 * \file ndarray_partition.h 
 * \brief DGL utilities for working with the partitioned NDArrays 
 */


#ifndef DGL_PARTITION_NDARRAY_PARTITION_H_
#define DGL_PARTITION_NDARRAY_PARTITION_H_

#include <dgl/runtime/object.h>
#include <dgl/array.h>
#include <utility>

namespace dgl {
namespace partition {

/**
 * @brief The top-level partition class. Specific types of partitions should be
 * sub-classes of this.
 */
class NDArrayPartition : public runtime::Object {
 public:
  /**
   * @brief Create a new partition.
   *
   * @param array_size The first dimension of the partitioned array.
   * @param num_parts The number parts to the array is split into.
   */
  NDArrayPartition(
      int64_t array_size,
      int num_parts);

  virtual ~NDArrayPartition() = default;

  static constexpr const char* _type_key = "partition.NDArrayPartition";

  DGL_DECLARE_OBJECT_TYPE_INFO(NDArrayPartition, Object);

  /**
   * @brief Create a mapping for the given indices to different partitions,
   * and a count of the number of indices per part.
   *
   * A prefix-sum of the counts, can be used to select the continuous sets of
   * indices destined for each part.
   *
   * @param in_idx The input indices to map.
   *
   * @return A pair containing 0) the permutation to re-order the indices by
   * partition, 1) the number of indices per partition (int64_t).
   */
  virtual std::pair<IdArray, NDArray>
  GeneratePermutation(
      IdArray in_idx) const = 0;

  /**
   * @brief Generate the local indices (the numbering within each processor)
   * from a set of global indices.
   *
   * @param in_idx The global indices.
   *
   * @return The local indices.
   */
  virtual IdArray MapToLocal(
      IdArray in_idx) const = 0;

  /**
   * @brief Get the first dimension of the partitioned array.
   *
   * @return The size.
   */
  int64_t ArraySize() const;

  /**
   * @brief Get the number of parts in this partition.
   *
   * @return The number of parts.
   */
  int NumParts() const;

 private:
  int64_t array_size_;
  int num_parts_;
};

DGL_DEFINE_OBJECT_REF(NDArrayPartitionRef, NDArrayPartition);

/**
 * @brief Create a new partition object, using the remainder of the row id
 * divided by the number of parts, to assign rows to parts.
 *
 * @param array_size The first dimension of the array.
 * @param num_parts The number of parts.
 *
 * @return The partition object.
 */
NDArrayPartitionRef CreatePartitionRemainderBased(
    int64_t array_size,
    int num_parts);

}  // namespace partition
}  // namespace dgl

#endif  // DGL_PARTITION_NDARRAY_PARTITION_H_
