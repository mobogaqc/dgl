#include <gtest/gtest.h>
#include <dgl/array.h>
#include "./common.h"

using namespace dgl;
using namespace dgl::runtime;

TEST(ArrayTest, TestCreate) {
  IdArray a = aten::NewIdArray(100, CTX, 32);
  ASSERT_EQ(a->dtype.bits, 32);
  ASSERT_EQ(a->shape[0], 100);

  a = aten::NewIdArray(0);
  ASSERT_EQ(a->shape[0], 0);

  std::vector<int64_t> vec = {2, 94, 232, 30};
  a = aten::VecToIdArray(vec, 32);
  ASSERT_EQ(Len(a), vec.size());
  ASSERT_EQ(a->dtype.bits, 32);
  for (int i = 0; i < Len(a); ++i) {
    ASSERT_EQ(Ptr<int32_t>(a)[i], vec[i]);
  }

  a = aten::VecToIdArray(std::vector<int32_t>());
  ASSERT_EQ(Len(a), 0);
};

void _TestRange(DLContext ctx) {
  IdArray a = aten::Range(10, 10, 64, ctx);
  ASSERT_EQ(Len(a), 0);
  a = aten::Range(10, 20, 32, ctx);
  ASSERT_EQ(Len(a), 10);
  ASSERT_EQ(a->dtype.bits, 32);
  a = a.CopyTo(CPU);
  for (int i = 0; i < 10; ++i)
    ASSERT_EQ(Ptr<int32_t>(a)[i], i + 10);
}

TEST(ArrayTest, TestRange) {
  _TestRange(CPU);
#ifdef DGL_USE_CUDA
  _TestRange(GPU);
#endif
};

TEST(ArrayTest, TestFull) {
  IdArray a = aten::Full(-100, 0, 32, CTX);
  ASSERT_EQ(Len(a), 0);
  a = aten::Full(-100, 13, 64, CTX);
  ASSERT_EQ(Len(a), 13);
  ASSERT_EQ(a->dtype.bits, 64);
  for (int i = 0; i < 13; ++i)
    ASSERT_EQ(Ptr<int64_t>(a)[i], -100);
};

TEST(ArrayTest, TestClone) {
  IdArray a = aten::NewIdArray(0);
  IdArray b = aten::Clone(a);
  ASSERT_EQ(Len(b), 0);

  a = aten::Range(0, 10, 32, CTX);
  b = aten::Clone(a);
  for (int i = 0; i < 10; ++i) {
    ASSERT_EQ(PI32(b)[i], i);
  }
  PI32(b)[0] = -1;
  for (int i = 0; i < 10; ++i) {
    ASSERT_EQ(PI32(a)[i], i);
  }
};

void _TestNumBits(DLContext ctx) {
  IdArray a = aten::Range(0, 10, 32, ctx);
  a = aten::AsNumBits(a, 64);
  ASSERT_EQ(a->dtype.bits, 64);
  a = a.CopyTo(CPU);
  for (int i = 0; i < 10; ++i)
    ASSERT_EQ(PI64(a)[i], i);
}

TEST(ArrayTest, TestAsNumBits) {
  _TestNumBits(CPU);
#ifdef DGL_USE_CUDA
  _TestNumBits(GPU);
#endif
};

template <typename IDX>
void _TestArith(DLContext ctx) {
  const int N = 100;
  IdArray a = aten::Full(-10, N, sizeof(IDX)*8, ctx);
  IdArray b = aten::Full(7, N, sizeof(IDX)*8, ctx);

  IdArray c = a + b;
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], -3);
  c = a - b;
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], -17);
  c = a * b;
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], -70);
  c = a / b;
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], -1);
  c = -a;
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], 10);

  const int val = -3;
  c = aten::Add(a, val);
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], -13);
  c = aten::Sub(a, val);
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], -7);
  c = aten::Mul(a, val);
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], 30);
  c = aten::Div(a, val);
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], 3);
  c = aten::Add(val, b);
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], 4);
  c = aten::Sub(val, b);
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], -10);
  c = aten::Mul(val, b);
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], -21);
  c = aten::Div(val, b);
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], 0);

  a = aten::Range(0, N, sizeof(IDX)*8, ctx);
  c = a < 50;
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], (int)(i < 50));

  c = a > 50;
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], (int)(i > 50));

  c = a >= 50;
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], (int)(i >= 50));

  c = a <= 50;
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], (int)(i <= 50));

  c = a == 50;
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], (int)(i == 50));

  c = a != 50;
  c = c.CopyTo(CPU);
  for (int i = 0; i < N; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], (int)(i != 50));

}

TEST(ArrayTest, TestArith) {
  _TestArith<int32_t>(CPU);
  _TestArith<int64_t>(CPU);
#ifdef DGL_USE_CUDA
  _TestArith<int32_t>(GPU);
  _TestArith<int64_t>(GPU);
#endif
};

template <typename IDX>
void _TestHStack() {
  IdArray a = aten::Range(0, 100, sizeof(IDX)*8, CTX);
  IdArray b = aten::Range(100, 200, sizeof(IDX)*8, CTX);
  IdArray c = aten::HStack(a, b);
  ASSERT_EQ(c->ndim, 1);
  ASSERT_EQ(c->shape[0], 200);
  for (int i = 0; i < 200; ++i)
    ASSERT_EQ(Ptr<IDX>(c)[i], i);
}

TEST(ArrayTest, TestHStack) {
  _TestHStack<int32_t>();
  _TestHStack<int64_t>();
}

template <typename IDX>
void _TestIndexSelect(DLContext ctx) {
  IdArray a = aten::Range(0, 100, sizeof(IDX)*8, ctx);
  ASSERT_EQ(aten::IndexSelect<int>(a, 50), 50);
  ASSERT_TRUE(ArrayEQ<IDX>(aten::IndexSelect(a, 10, 20),
        aten::Range(10, 20, sizeof(IDX)*8, ctx)));
  IdArray b = aten::VecToIdArray(std::vector<IDX>({0, 20, 10}), sizeof(IDX)*8, ctx);
  IdArray c = aten::IndexSelect(a, b);
  ASSERT_TRUE(ArrayEQ<IDX>(b, c));
}

TEST(ArrayTest, TestIndexSelect) {
  _TestIndexSelect<int32_t>(CPU);
  _TestIndexSelect<int64_t>(CPU);
#ifdef DGL_USE_CUDA
  _TestIndexSelect<int32_t>(GPU);
  _TestIndexSelect<int64_t>(GPU);
#endif
}

template <typename IDX>
void _TestRelabel_() {
  IdArray a = aten::VecToIdArray(std::vector<IDX>({0, 20, 10}), sizeof(IDX)*8, CTX);
  IdArray b = aten::VecToIdArray(std::vector<IDX>({20, 5, 6}), sizeof(IDX)*8, CTX);
  IdArray c = aten::Relabel_({a, b});
  IdArray ta = aten::VecToIdArray(std::vector<IDX>({0, 1, 2}), sizeof(IDX)*8, CTX);
  IdArray tb = aten::VecToIdArray(std::vector<IDX>({1, 3, 4}), sizeof(IDX)*8, CTX);
  IdArray tc = aten::VecToIdArray(std::vector<IDX>({0, 20, 10, 5, 6}), sizeof(IDX)*8, CTX);
  ASSERT_TRUE(ArrayEQ<IDX>(a, ta));
  ASSERT_TRUE(ArrayEQ<IDX>(b, tb));
  ASSERT_TRUE(ArrayEQ<IDX>(c, tc));
}

TEST(ArrayTest, TestRelabel_) {
  _TestRelabel_<int32_t>();
  _TestRelabel_<int64_t>();
}

template <typename IDX>
void _TestCumSum(DLContext ctx) {
  IdArray a = aten::VecToIdArray(std::vector<IDX>({8, 6, 7, 5, 3, 0, 9}),
      sizeof(IDX)*8, ctx);
  {
    IdArray tb = aten::VecToIdArray(std::vector<IDX>({8, 14, 21, 26, 29, 29, 38}),
        sizeof(IDX)*8, ctx);
    IdArray b = aten::CumSum(a);
    ASSERT_TRUE(ArrayEQ<IDX>(b, tb));
  }
  {
    IdArray tb = aten::VecToIdArray(std::vector<IDX>({0, 8, 14, 21, 26, 29, 29, 38}),
        sizeof(IDX)*8, ctx);
    IdArray b = aten::CumSum(a, true);
    ASSERT_TRUE(ArrayEQ<IDX>(b, tb));
  }
  a = aten::VecToIdArray(std::vector<IDX>({}), sizeof(IDX)*8, ctx);
  {
    IdArray tb = aten::VecToIdArray(std::vector<IDX>({}), sizeof(IDX)*8, ctx);
    IdArray b = aten::CumSum(a);
    ASSERT_TRUE(ArrayEQ<IDX>(b, tb));
  }
  {
    IdArray tb = aten::VecToIdArray(std::vector<IDX>({}), sizeof(IDX)*8, ctx);
    IdArray b = aten::CumSum(a);
    ASSERT_TRUE(ArrayEQ<IDX>(b, tb));
  }
}

TEST(ArrayTest, CumSum) {
  _TestCumSum<int32_t>(CPU);
  _TestCumSum<int64_t>(CPU);
#ifdef DGL_USE_CUDA
  _TestCumSum<int32_t>(GPU);
  _TestCumSum<int64_t>(GPU);
#endif
}
