/**
 *  Copyright (c) 2022 by Contributors
 * @file utils.h
 * @brief DGL C++ sparse API utilities
 */
#ifndef DGL_SPARSE_UTILS_H_
#define DGL_SPARSE_UTILS_H_

#include <dmlc/logging.h>
#include <sparse/sparse_matrix.h>

namespace dgl {
namespace sparse {

/** @brief Find a proper sparse format for two sparse matrices. It chooses
 * COO if anyone of the sparse matrices has COO format. If none of them has
 * COO, it tries CSR and CSC in the same manner. */
inline static SparseFormat FindAnyExistingFormat(
    const c10::intrusive_ptr<SparseMatrix>& A,
    const c10::intrusive_ptr<SparseMatrix>& B) {
  SparseFormat fmt;
  if (A->HasCOO() || B->HasCOO()) {
    fmt = SparseFormat::kCOO;
  } else if (A->HasCSR() || B->HasCSR()) {
    fmt = SparseFormat::kCSR;
  } else {
    fmt = SparseFormat::kCSC;
  }
  return fmt;
}

/** @brief Check whether two matrices has the same dtype and shape for
 * elementwise operators. */
inline static void ElementwiseOpSanityCheck(
    const c10::intrusive_ptr<SparseMatrix>& A,
    const c10::intrusive_ptr<SparseMatrix>& B) {
  CHECK(A->value().dtype() == B->value().dtype())
      << "Elementwise operators do not support two sparse matrices with "
         "different dtypes. ("
      << A->value().dtype() << " vs " << B->value().dtype() << ")";
  CHECK(A->shape()[0] == B->shape()[0] && A->shape()[1] == B->shape()[1])
      << "Elementwise operator do not support two sparse matrices with "
         "different shapes. (["
      << A->shape()[0] << ", " << A->shape()[1] << "] vs [" << B->shape()[0]
      << ", " << B->shape()[1] << "])";
}

}  // namespace sparse
}  // namespace dgl

#endif  // DGL_SPARSE_UTILS_H_
