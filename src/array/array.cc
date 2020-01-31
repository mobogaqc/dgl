/*!
 *  Copyright (c) 2019 by Contributors
 * \file array/array.cc
 * \brief DGL array utilities implementation
 */
#include <dgl/array.h>
#include "../c_api_common.h"
#include "./array_op.h"
#include "./arith.h"

namespace dgl {

using runtime::NDArray;

namespace aten {

IdArray NewIdArray(int64_t length, DLContext ctx, uint8_t nbits) {
  return IdArray::Empty({length}, DLDataType{kDLInt, nbits, 1}, ctx);
}

IdArray Clone(IdArray arr) {
  IdArray ret = NewIdArray(arr->shape[0], arr->ctx, arr->dtype.bits);
  ret.CopyFrom(arr);
  return ret;
}

IdArray Range(int64_t low, int64_t high, uint8_t nbits, DLContext ctx) {
  IdArray ret;
  ATEN_XPU_SWITCH(ctx.device_type, XPU, {
    if (nbits == 32) {
      ret = impl::Range<XPU, int32_t>(low, high, ctx);
    } else if (nbits == 64) {
      ret = impl::Range<XPU, int64_t>(low, high, ctx);
    } else {
      LOG(FATAL) << "Only int32 or int64 is supported.";
    }
  });
  return ret;
}

IdArray Full(int64_t val, int64_t length, uint8_t nbits, DLContext ctx) {
  IdArray ret;
  ATEN_XPU_SWITCH(ctx.device_type, XPU, {
    if (nbits == 32) {
      ret = impl::Full<XPU, int32_t>(val, length, ctx);
    } else if (nbits == 64) {
      ret = impl::Full<XPU, int64_t>(val, length, ctx);
    } else {
      LOG(FATAL) << "Only int32 or int64 is supported.";
    }
  });
  return ret;
}

IdArray AsNumBits(IdArray arr, uint8_t bits) {
  IdArray ret;
  ATEN_XPU_SWITCH(arr->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(arr->dtype, IdType, {
      ret = impl::AsNumBits<XPU, IdType>(arr, bits);
    });
  });
  return ret;
}

IdArray Add(IdArray lhs, IdArray rhs) {
  IdArray ret;
  CHECK_EQ(lhs->ctx, rhs->ctx) << "Both operands should have the same device context";
  CHECK_EQ(lhs->dtype, rhs->dtype) << "Both operands should have the same dtype";
  ATEN_XPU_SWITCH(lhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(lhs->dtype, IdType, {
      ret = impl::BinaryElewise<XPU, IdType, arith::Add>(lhs, rhs);
    });
  });
  return ret;
}

IdArray Sub(IdArray lhs, IdArray rhs) {
  IdArray ret;
  CHECK_EQ(lhs->ctx, rhs->ctx) << "Both operands should have the same device context";
  CHECK_EQ(lhs->dtype, rhs->dtype) << "Both operands should have the same dtype";
  ATEN_XPU_SWITCH(lhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(lhs->dtype, IdType, {
      ret = impl::BinaryElewise<XPU, IdType, arith::Sub>(lhs, rhs);
    });
  });
  return ret;
}

IdArray Mul(IdArray lhs, IdArray rhs) {
  IdArray ret;
  CHECK_EQ(lhs->ctx, rhs->ctx) << "Both operands should have the same device context";
  CHECK_EQ(lhs->dtype, rhs->dtype) << "Both operands should have the same dtype";
  ATEN_XPU_SWITCH(lhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(lhs->dtype, IdType, {
      ret = impl::BinaryElewise<XPU, IdType, arith::Mul>(lhs, rhs);
    });
  });
  return ret;
}

IdArray Div(IdArray lhs, IdArray rhs) {
  IdArray ret;
  CHECK_EQ(lhs->ctx, rhs->ctx) << "Both operands should have the same device context";
  CHECK_EQ(lhs->dtype, rhs->dtype) << "Both operands should have the same dtype";
  ATEN_XPU_SWITCH(lhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(lhs->dtype, IdType, {
      ret = impl::BinaryElewise<XPU, IdType, arith::Div>(lhs, rhs);
    });
  });
  return ret;
}

IdArray Add(IdArray lhs, dgl_id_t rhs) {
  IdArray ret;
  ATEN_XPU_SWITCH(lhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(lhs->dtype, IdType, {
      ret = impl::BinaryElewise<XPU, IdType, arith::Add>(lhs, rhs);
    });
  });
  return ret;
}

IdArray Sub(IdArray lhs, dgl_id_t rhs) {
  IdArray ret;
  ATEN_XPU_SWITCH(lhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(lhs->dtype, IdType, {
      ret = impl::BinaryElewise<XPU, IdType, arith::Sub>(lhs, rhs);
    });
  });
  return ret;
}

IdArray Mul(IdArray lhs, dgl_id_t rhs) {
  IdArray ret;
  ATEN_XPU_SWITCH(lhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(lhs->dtype, IdType, {
      ret = impl::BinaryElewise<XPU, IdType, arith::Mul>(lhs, rhs);
    });
  });
  return ret;
}

IdArray Div(IdArray lhs, dgl_id_t rhs) {
  IdArray ret;
  ATEN_XPU_SWITCH(lhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(lhs->dtype, IdType, {
      ret = impl::BinaryElewise<XPU, IdType, arith::Div>(lhs, rhs);
    });
  });
  return ret;
}

IdArray Add(dgl_id_t lhs, IdArray rhs) {
  return Add(rhs, lhs);
}

IdArray Sub(dgl_id_t lhs, IdArray rhs) {
  IdArray ret;
  ATEN_XPU_SWITCH(rhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(rhs->dtype, IdType, {
      ret = impl::BinaryElewise<XPU, IdType, arith::Sub>(lhs, rhs);
    });
  });
  return ret;
}

IdArray Mul(dgl_id_t lhs, IdArray rhs) {
  return Mul(rhs, lhs);
}

IdArray Div(dgl_id_t lhs, IdArray rhs) {
  IdArray ret;
  ATEN_XPU_SWITCH(rhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(rhs->dtype, IdType, {
      ret = impl::BinaryElewise<XPU, IdType, arith::Div>(lhs, rhs);
    });
  });
  return ret;
}

BoolArray LT(IdArray lhs, dgl_id_t rhs) {
  BoolArray ret;
  ATEN_XPU_SWITCH(lhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(lhs->dtype, IdType, {
      ret = impl::BinaryElewise<XPU, IdType, arith::LT>(lhs, rhs);
    });
  });
  return ret;
}

IdArray HStack(IdArray lhs, IdArray rhs) {
  IdArray ret;
  CHECK_EQ(lhs->ctx, rhs->ctx) << "Both operands should have the same device context";
  CHECK_EQ(lhs->dtype, rhs->dtype) << "Both operands should have the same dtype";
  ATEN_XPU_SWITCH(lhs->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(lhs->dtype, IdType, {
      ret = impl::HStack<XPU, IdType>(lhs, rhs);
    });
  });
  return ret;
}

NDArray IndexSelect(NDArray array, IdArray index) {
  NDArray ret;
  // TODO(BarclayII): check if array and index match in context
  ATEN_XPU_SWITCH(array->ctx.device_type, XPU, {
    ATEN_DTYPE_SWITCH(array->dtype, DType, "values", {
      ATEN_ID_TYPE_SWITCH(index->dtype, IdType, {
        ret = impl::IndexSelect<XPU, DType, IdType>(array, index);
      });
    });
  });
  return ret;
}

template<typename ValueType>
ValueType IndexSelect(NDArray array, uint64_t index) {
  ValueType ret = 0;
  ATEN_XPU_SWITCH(array->ctx.device_type, XPU, {
    ATEN_DTYPE_SWITCH(array->dtype, DType, "values", {
      ret = impl::IndexSelect<XPU, DType>(array, index);
    });
  });
  return ret;
}
template int32_t IndexSelect<int32_t>(NDArray array, uint64_t index);
template int64_t IndexSelect<int64_t>(NDArray array, uint64_t index);
template uint32_t IndexSelect<uint32_t>(NDArray array, uint64_t index);
template uint64_t IndexSelect<uint64_t>(NDArray array, uint64_t index);
template float IndexSelect<float>(NDArray array, uint64_t index);
template double IndexSelect<double>(NDArray array, uint64_t index);

IdArray Relabel_(const std::vector<IdArray>& arrays) {
  IdArray ret;
  ATEN_XPU_SWITCH(arrays[0]->ctx.device_type, XPU, {
    ATEN_ID_TYPE_SWITCH(arrays[0]->dtype, IdType, {
      ret = impl::Relabel_<XPU, IdType>(arrays);
    });
  });
  return ret;
}

template<typename ValueType>
std::tuple<NDArray, IdArray, IdArray> Pack(NDArray array, ValueType pad_value) {
  std::tuple<NDArray, IdArray, IdArray> ret;
  ATEN_XPU_SWITCH(array->ctx.device_type, XPU, {
    ATEN_DTYPE_SWITCH(array->dtype, DType, "array", {
      ret = impl::Pack<XPU, DType>(array, static_cast<DType>(pad_value));
    });
  });
  return ret;
}

template std::tuple<NDArray, IdArray, IdArray> Pack<int32_t>(NDArray, int32_t);
template std::tuple<NDArray, IdArray, IdArray> Pack<int64_t>(NDArray, int64_t);
template std::tuple<NDArray, IdArray, IdArray> Pack<uint32_t>(NDArray, uint32_t);
template std::tuple<NDArray, IdArray, IdArray> Pack<uint64_t>(NDArray, uint64_t);
template std::tuple<NDArray, IdArray, IdArray> Pack<float>(NDArray, float);
template std::tuple<NDArray, IdArray, IdArray> Pack<double>(NDArray, double);

std::pair<NDArray, IdArray> ConcatSlices(NDArray array, IdArray lengths) {
  std::pair<NDArray, IdArray> ret;
  ATEN_XPU_SWITCH(array->ctx.device_type, XPU, {
    ATEN_DTYPE_SWITCH(array->dtype, DType, "array", {
      ATEN_ID_TYPE_SWITCH(lengths->dtype, IdType, {
        ret = impl::ConcatSlices<XPU, DType, IdType>(array, lengths);
      });
    });
  });
  return ret;
}

///////////////////////// CSR routines //////////////////////////

bool CSRIsNonZero(CSRMatrix csr, int64_t row, int64_t col) {
  bool ret = false;
  ATEN_CSR_IDX_SWITCH(csr, XPU, IdType, {
    ret = impl::CSRIsNonZero<XPU, IdType>(csr, row, col);
  });
  return ret;
}

NDArray CSRIsNonZero(CSRMatrix csr, NDArray row, NDArray col) {
  NDArray ret;
  ATEN_CSR_IDX_SWITCH(csr, XPU, IdType, {
    ret = impl::CSRIsNonZero<XPU, IdType>(csr, row, col);
  });
  return ret;
}

bool CSRHasDuplicate(CSRMatrix csr) {
  bool ret = false;
  ATEN_CSR_IDX_SWITCH(csr, XPU, IdType, {
    ret = impl::CSRHasDuplicate<XPU, IdType>(csr);
  });
  return ret;
}

int64_t CSRGetRowNNZ(CSRMatrix csr, int64_t row) {
  int64_t ret = 0;
  ATEN_CSR_IDX_SWITCH(csr, XPU, IdType, {
    ret = impl::CSRGetRowNNZ<XPU, IdType>(csr, row);
  });
  return ret;
}

NDArray CSRGetRowNNZ(CSRMatrix csr, NDArray row) {
  NDArray ret;
  ATEN_CSR_IDX_SWITCH(csr, XPU, IdType, {
    ret = impl::CSRGetRowNNZ<XPU, IdType>(csr, row);
  });
  return ret;
}

NDArray CSRGetRowColumnIndices(CSRMatrix csr, int64_t row) {
  NDArray ret;
  ATEN_CSR_IDX_SWITCH(csr, XPU, IdType, {
    ret = impl::CSRGetRowColumnIndices<XPU, IdType>(csr, row);
  });
  return ret;
}

NDArray CSRGetRowData(CSRMatrix csr, int64_t row) {
  NDArray ret;
  ATEN_CSR_SWITCH(csr, XPU, IdType, DType, {
    ret = impl::CSRGetRowData<XPU, IdType, DType>(csr, row);
  });
  return ret;
}

NDArray CSRGetData(CSRMatrix csr, int64_t row, int64_t col) {
  NDArray ret;
  ATEN_CSR_SWITCH(csr, XPU, IdType, DType, {
    ret = impl::CSRGetData<XPU, IdType, DType>(csr, row, col);
  });
  return ret;
}

NDArray CSRGetData(CSRMatrix csr, NDArray rows, NDArray cols) {
  NDArray ret;
  ATEN_CSR_SWITCH(csr, XPU, IdType, DType, {
    ret = impl::CSRGetData<XPU, IdType, DType>(csr, rows, cols);
  });
  return ret;
}

std::vector<NDArray> CSRGetDataAndIndices(
    CSRMatrix csr, NDArray rows, NDArray cols) {
  std::vector<NDArray> ret;
  ATEN_CSR_SWITCH(csr, XPU, IdType, DType, {
    ret = impl::CSRGetDataAndIndices<XPU, IdType, DType>(csr, rows, cols);
  });
  return ret;
}

CSRMatrix CSRTranspose(CSRMatrix csr) {
  CSRMatrix ret;
  ATEN_CSR_SWITCH(csr, XPU, IdType, DType, {
    ret = impl::CSRTranspose<XPU, IdType, DType>(csr);
  });
  return ret;
}

COOMatrix CSRToCOO(CSRMatrix csr, bool data_as_order) {
  COOMatrix ret;
  if (data_as_order) {
    ATEN_XPU_SWITCH(csr.indptr->ctx.device_type, XPU, {
      ATEN_ID_TYPE_SWITCH(csr.indptr->dtype, IdType, {
        ret = impl::CSRToCOODataAsOrder<XPU, IdType>(csr);
      });
    });
  } else {
    ATEN_XPU_SWITCH(csr.indptr->ctx.device_type, XPU, {
      ATEN_ID_TYPE_SWITCH(csr.indptr->dtype, IdType, {
        ret = impl::CSRToCOO<XPU, IdType>(csr);
      });
    });
  }
  return ret;
}

CSRMatrix CSRSliceRows(CSRMatrix csr, int64_t start, int64_t end) {
  CSRMatrix ret;
  ATEN_CSR_SWITCH(csr, XPU, IdType, DType, {
    ret = impl::CSRSliceRows<XPU, IdType, DType>(csr, start, end);
  });
  return ret;
}

CSRMatrix CSRSliceRows(CSRMatrix csr, NDArray rows) {
  CSRMatrix ret;
  ATEN_CSR_SWITCH(csr, XPU, IdType, DType, {
    ret = impl::CSRSliceRows<XPU, IdType, DType>(csr, rows);
  });
  return ret;
}

CSRMatrix CSRSliceMatrix(CSRMatrix csr, NDArray rows, NDArray cols) {
  CSRMatrix ret;
  ATEN_CSR_SWITCH(csr, XPU, IdType, DType, {
    ret = impl::CSRSliceMatrix<XPU, IdType, DType>(csr, rows, cols);
  });
  return ret;
}

void CSRSort(CSRMatrix csr) {
  ATEN_CSR_SWITCH(csr, XPU, IdType, DType, {
    impl::CSRSort<XPU, IdType, DType>(csr);
  });
}

///////////////////////// COO routines //////////////////////////

bool COOHasDuplicate(COOMatrix coo) {
  bool ret = false;
  ATEN_COO_IDX_SWITCH(coo, XPU, IdType, {
    ret = impl::COOHasDuplicate<XPU, IdType>(coo);
  });
  return ret;
}

CSRMatrix COOToCSR(COOMatrix coo) {
  CSRMatrix ret;
  ATEN_COO_SWITCH(coo, XPU, IdType, DType, {
    ret = impl::COOToCSR<XPU, IdType, DType>(coo);
  });
  return ret;
}

}  // namespace aten
}  // namespace dgl
