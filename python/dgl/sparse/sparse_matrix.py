"""DGL sparse matrix module."""
# pylint: disable= invalid-name
from typing import Optional, Tuple

import torch


class SparseMatrix:
    r"""Class for sparse matrix."""

    def __init__(self, c_sparse_matrix: torch.ScriptObject):
        self.c_sparse_matrix = c_sparse_matrix

    def __repr__(self):
        return _sparse_matrix_str(self)

    @property
    def val(self) -> torch.Tensor:
        """Returns the values of the non-zero elements.

        Returns
        -------
        torch.Tensor
            Values of the non-zero elements
        """
        return self.c_sparse_matrix.val()

    @property
    def shape(self) -> Tuple[int]:
        """Returns the shape of the sparse matrix.

        Returns
        -------
        Tuple[int]
            The shape of the sparse matrix
        """
        return tuple(self.c_sparse_matrix.shape())

    @property
    def nnz(self) -> int:
        """Returns the number of non-zero elements in the sparse matrix.

        Returns
        -------
        int
            The number of non-zero elements of the matrix
        """
        return self.c_sparse_matrix.nnz()

    @property
    def dtype(self) -> torch.dtype:
        """Returns the data type of the sparse matrix.

        Returns
        -------
        torch.dtype
            Data type of the sparse matrix
        """
        return self.c_sparse_matrix.val().dtype

    @property
    def device(self) -> torch.device:
        """Returns the device the sparse matrix is on.

        Returns
        -------
        torch.device
            The device the sparse matrix is on
        """
        return self.c_sparse_matrix.device()

    @property
    def row(self) -> torch.Tensor:
        """Returns the row indices of the non-zero elements.

        Returns
        -------
        torch.Tensor
            Row indices of the non-zero elements
        """
        return self.coo()[0]

    @property
    def col(self) -> torch.Tensor:
        """Returns the column indices of the non-zero elements.

        Returns
        -------
        torch.Tensor
            Column indices of the non-zero elements
        """
        return self.coo()[1]

    def coo(self) -> Tuple[torch.Tensor, ...]:
        """Returns the coordinate (COO) representation of the sparse matrix.

        Returns
        -------
        Tuple[torch.Tensor, torch.Tensor]
            A tuple of tensors containing row and column coordinates
        """
        return self.c_sparse_matrix.coo()

    def csr(self) -> Tuple[torch.Tensor, ...]:
        r"""Returns the compressed sparse row (CSR) representation of the sparse
        matrix.

        Returns
        -------
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor]
            A tuple of tensors containing row indptr, column indices and value
            indices. Value indices is an index tensor, indicating the order of
            the values of non-zero elements in the CSR representation. A null
            value indices indicates the order of the values stays the same as
            the values of the SparseMatrix.
        """
        return self.c_sparse_matrix.csr()

    def csc(self) -> Tuple[torch.Tensor, ...]:
        r"""Returns the compressed sparse column (CSC) representation of the
        sparse matrix.

        Returns
        -------
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor]
            A tuple of tensors containing column indptr, row indices and value
            indices. Value indices is an index tensor, indicating the order of
            the values of non-zero elements in the CSC representation. A null
            value indices indicates the order of the values stays the same as
            the values of the SparseMatrix.
        """
        return self.c_sparse_matrix.csc()

    def to_dense(self) -> torch.Tensor:
        """Returns a copy in dense matrix format of the sparse matrix.

        Returns
        -------
        torch.Tensor
            The copy in dense matrix format
        """
        row, col = self.coo()
        val = self.val
        shape = self.shape + val.shape[1:]
        mat = torch.zeros(shape, device=self.device, dtype=self.dtype)
        mat[row, col] = val
        return mat

    def t(self):
        """Alias of :meth:`transpose()`"""
        return self.transpose()

    @property
    def T(self):  # pylint: disable=C0103
        """Alias of :meth:`transpose()`"""
        return self.transpose()

    def transpose(self):
        """Returns the transpose of this sparse matrix.

        Returns
        -------
        SparseMatrix
            The transpose of this sparse matrix.

        Example
        -------

        >>> row = torch.tensor([1, 1, 3])
        >>> col = torch.tensor([2, 1, 3])
        >>> val = torch.tensor([1, 1, 2])
        >>> A = dglsp.from_coo(row, col, val)
        >>> A = A.transpose()
        SparseMatrix(indices=tensor([[2, 1, 3],
                                     [1, 1, 3]]),
                     values=tensor([1, 1, 2]),
                     shape=(4, 4), nnz=3)
        """
        return SparseMatrix(self.c_sparse_matrix.transpose())

    def to(self, device=None, dtype=None):
        """Performs matrix dtype and/or device conversion. If the target device
        and dtype are already in use, the original matrix will be returned.

        Parameters
        ----------
        device : torch.device, optional
            The target device of the matrix if provided, otherwise the current
            device will be used
        dtype : torch.dtype, optional
            The target data type of the matrix values if provided, otherwise the
            current data type will be used

        Returns
        -------
        SparseMatrix
            The converted matrix

        Example
        --------

        >>> row = torch.tensor([1, 1, 2])
        >>> col = torch.tensor([1, 2, 0])
        >>> A = dglsp.from_coo(row, col, shape=(3, 4))
        >>> A.to(device='cuda:0', dtype=torch.int32)
        SparseMatrix(indices=tensor([[1, 1, 2],
                                     [1, 2, 0]], device='cuda:0'),
                     values=tensor([1, 1, 1], device='cuda:0',
                                   dtype=torch.int32),
                     shape=(3, 4), nnz=3)
        """
        if device is None:
            device = self.device
        if dtype is None:
            dtype = self.dtype

        if device == self.device and dtype == self.dtype:
            return self
        elif device == self.device:
            return val_like(self, self.val.to(dtype=dtype))
        else:
            # TODO(#5119): Find a better moving strategy instead of always
            # convert to COO format.
            row, col = self.coo()
            row = row.to(device=device)
            col = col.to(device=device)
            val = self.val.to(device=device, dtype=dtype)
            return from_coo(row, col, val, self.shape)

    def cuda(self):
        """Moves the matrix to GPU. If the matrix is already on GPU, the
        original matrix will be returned. If multiple GPU devices exist,
        'cuda:0' will be selected.

        Returns
        -------
        SparseMatrix
            The matrix on GPU

        Example
        --------

        >>> row = torch.tensor([1, 1, 2])
        >>> col = torch.tensor([1, 2, 0])
        >>> A = dglsp.from_coo(row, col, shape=(3, 4))
        >>> A.cuda()
        SparseMatrix(indices=tensor([[1, 1, 2],
                                     [1, 2, 0]], device='cuda:0'),
                     values=tensor([1., 1., 1.], device='cuda:0'),
                     shape=(3, 4), nnz=3)
        """
        return self.to(device="cuda")

    def cpu(self):
        """Moves the matrix to CPU. If the matrix is already on CPU, the
        original matrix will be returned.

        Returns
        -------
        SparseMatrix
            The matrix on CPU

        Example
        --------

        >>> row = torch.tensor([1, 1, 2]).to('cuda')
        >>> col = torch.tensor([1, 2, 0]).to('cuda')
        >>> A = dglsp.from_coo(row, col, shape=(3, 4))
        >>> A.cpu()
        SparseMatrix(indices=tensor([[1, 1, 2],
                                     [1, 2, 0]]),
                     values=tensor([1., 1., 1.]),
                     shape=(3, 4), nnz=3)
        """
        return self.to(device="cpu")

    def float(self):
        """Converts the matrix values to float data type. If the matrix already
        uses float data type, the original matrix will be returned.

        Returns
        -------
        SparseMatrix
            The matrix with float values

        Example
        --------

        >>> row = torch.tensor([1, 1, 2])
        >>> col = torch.tensor([1, 2, 0])
        >>> val = torch.ones(len(row)).long()
        >>> A = dglsp.from_coo(row, col, val, shape=(3, 4))
        >>> A.float()
        SparseMatrix(indices=tensor([[1, 1, 2],
                                     [1, 2, 0]]),
                     values=tensor([1., 1., 1.]),
                     shape=(3, 4), nnz=3)
        """
        return self.to(dtype=torch.float)

    def double(self):
        """Converts the matrix values to double data type. If the matrix already
        uses double data type, the original matrix will be returned.

        Returns
        -------
        SparseMatrix
            The matrix with double values

        Example
        --------

        >>> row = torch.tensor([1, 1, 2])
        >>> col = torch.tensor([1, 2, 0])
        >>> A = dglsp.from_coo(row, col, shape=(3, 4))
        >>> A.double()
        SparseMatrix(indices=tensor([[1, 1, 2],
                                     [1, 2, 0]]),
                     values=tensor([1., 1., 1.], dtype=torch.float64),
                     shape=(3, 4), nnz=3)
        """
        return self.to(dtype=torch.double)

    def int(self):
        """Converts the matrix values to int data type. If the matrix already
        uses int data type, the original matrix will be returned.

        Returns
        -------
        DiagMatrix
            The matrix with int values

        Example
        --------

        >>> row = torch.tensor([1, 1, 2])
        >>> col = torch.tensor([1, 2, 0])
        >>> A = dglsp.from_coo(row, col, shape=(3, 4))
        >>> A.int()
        SparseMatrix(indices=tensor([[1, 1, 2],
                                     [1, 2, 0]]),
                     values=tensor([1, 1, 1], dtype=torch.int32),
                     shape=(3, 4), nnz=3)
        """
        return self.to(dtype=torch.int)

    def long(self):
        """Converts the matrix values to long data type. If the matrix already
        uses long data type, the original matrix will be returned.

        Returns
        -------
        DiagMatrix
            The matrix with long values

        Example
        --------

        >>> row = torch.tensor([1, 1, 2])
        >>> col = torch.tensor([1, 2, 0])
        >>> A = dglsp.from_coo(row, col, shape=(3, 4))
        >>> A.long()
        SparseMatrix(indices=tensor([[1, 1, 2],
                                     [1, 2, 0]]),
                     values=tensor([1, 1, 1]),
                     shape=(3, 4), nnz=3)
        """
        return self.to(dtype=torch.long)

    def coalesce(self):
        """Returns a coalesced sparse matrix.

        A coalesced sparse matrix satisfies the following properties:

          - the indices of the non-zero elements are unique,
          - the indices are sorted in lexicographical order.

        The coalescing process will accumulate the non-zero elements of the same
        indices by summation.

        The function does not support autograd.

        Returns
        -------
        SparseMatrix
            The coalesced sparse matrix

        Examples
        --------
        >>> row = torch.tensor([1, 0, 0, 0, 1])
        >>> col = torch.tensor([1, 1, 1, 2, 2])
        >>> val = torch.tensor([0, 1, 2, 3, 4])
        >>> A = dglsp.from_coo(row, col, val)
        >>> A.coalesce()
        SparseMatrix(indices=tensor([[0, 0, 1, 1],
                                     [1, 2, 1, 2]]),
                     values=tensor([3, 3, 0, 4]),
                     shape=(2, 3), nnz=4)
        """
        return SparseMatrix(self.c_sparse_matrix.coalesce())

    def has_duplicate(self):
        """Returns ``True`` if the sparse matrix contains duplicate indices.

        Examples
        --------
        >>> row = torch.tensor([1, 0, 0, 0, 1])
        >>> col = torch.tensor([1, 1, 1, 2, 2])
        >>> val = torch.tensor([0, 1, 2, 3, 4])
        >>> A = dglsp.from_coo(row, col, val)
        >>> A.has_duplicate()
        True
        >>> A.coalesce().has_duplicate()
        False
        """
        return self.c_sparse_matrix.has_duplicate()


def from_coo(
    row: torch.Tensor,
    col: torch.Tensor,
    val: Optional[torch.Tensor] = None,
    shape: Optional[Tuple[int, int]] = None,
) -> SparseMatrix:
    r"""Creates a sparse matrix from row and column coordinates.

    Parameters
    ----------
    row : torch.Tensor
        The row indices of shape (nnz)
    col : torch.Tensor
        The column indices of shape (nnz)
    val : torch.Tensor, optional
        The values of shape (nnz) or (nnz, D). If None, it will be a tensor of
        shape (nnz) filled by 1.
    shape : tuple[int, int], optional
        If not specified, it will be inferred from :attr:`row` and :attr:`col`,
        i.e., (row.max() + 1, col.max() + 1). Otherwise, :attr:`shape` should
        be no smaller than this.

    Returns
    -------
    SparseMatrix
        Sparse matrix

    Examples
    --------

    Case1: Sparse matrix with row and column indices without values.

    >>> dst = torch.tensor([1, 1, 2])
    >>> src = torch.tensor([2, 4, 3])
    >>> A = dglsp.from_coo(dst, src)
    SparseMatrix(indices=tensor([[1, 1, 2],
                                 [2, 4, 3]]),
                 values=tensor([1., 1., 1.]),
                 shape=(3, 5), nnz=3)
    >>> # Specify shape
    >>> A = dglsp.from_coo(dst, src, shape=(5, 5))
    SparseMatrix(indices=tensor([[1, 1, 2],
                                 [2, 4, 3]]),
                 values=tensor([1., 1., 1.]),
                 shape=(5, 5), nnz=3)

    Case2: Sparse matrix with scalar/vector values. Following example is with
    vector data.

    >>> dst = torch.tensor([1, 1, 2])
    >>> src = torch.tensor([2, 4, 3])
    >>> val = torch.tensor([[1., 1.], [2., 2.], [3., 3.]])
    >>> A = dglsp.from_coo(dst, src, val)
    SparseMatrix(indices=tensor([[1, 1, 2],
                                 [2, 4, 3]]),
                 values=tensor([[1., 1.],
                                [2., 2.],
                                [3., 3.]]),
                 shape=(3, 5), nnz=3, val_size=(2,))
    """
    if shape is None:
        shape = (torch.max(row).item() + 1, torch.max(col).item() + 1)
    if val is None:
        val = torch.ones(row.shape[0]).to(row.device)

    return SparseMatrix(torch.ops.dgl_sparse.from_coo(row, col, val, shape))


def from_csr(
    indptr: torch.Tensor,
    indices: torch.Tensor,
    val: Optional[torch.Tensor] = None,
    shape: Optional[Tuple[int, int]] = None,
) -> SparseMatrix:
    r"""Creates a sparse matrix from CSR indices.

    For row i of the sparse matrix

    - the column indices of the non-zero elements are stored in
      ``indices[indptr[i]: indptr[i+1]]``
    - the corresponding values are stored in ``val[indptr[i]: indptr[i+1]]``

    Parameters
    ----------
    indptr : torch.Tensor
        Pointer to the column indices of shape (N + 1), where N is the number
        of rows
    indices : torch.Tensor
        The column indices of shape (nnz)
    val : torch.Tensor, optional
        The values of shape (nnz) or (nnz, D). If None, it will be a tensor of
        shape (nnz) filled by 1.
    shape : tuple[int, int], optional
        If not specified, it will be inferred from :attr:`indptr` and
        :attr:`indices`, i.e., (len(indptr) - 1, indices.max() + 1). Otherwise,
        :attr:`shape` should be no smaller than this.

    Returns
    -------
    SparseMatrix
        Sparse matrix

    Examples
    --------

    Case1: Sparse matrix without values

    [[0, 1, 0],
     [0, 0, 1],
     [1, 1, 1]]

    >>> indptr = torch.tensor([0, 1, 2, 5])
    >>> indices = torch.tensor([1, 2, 0, 1, 2])
    >>> A = dglsp.from_csr(indptr, indices)
    SparseMatrix(indices=tensor([[0, 1, 2, 2, 2],
                                 [1, 2, 0, 1, 2]]),
                 values=tensor([1., 1., 1., 1., 1.]),
                 shape=(3, 3), nnz=5)
    >>> # Specify shape
    >>> A = dglsp.from_csr(indptr, indices, shape=(3, 5))
    SparseMatrix(indices=tensor([[0, 1, 2, 2, 2],
                                 [1, 2, 0, 1, 2]]),
                 values=tensor([1., 1., 1., 1., 1.]),
                 shape=(3, 5), nnz=5)

    Case2: Sparse matrix with scalar/vector values. Following example is with
    vector data.

    >>> indptr = torch.tensor([0, 1, 2, 5])
    >>> indices = torch.tensor([1, 2, 0, 1, 2])
    >>> val = torch.tensor([[1, 1], [2, 2], [3, 3], [4, 4], [5, 5]])
    >>> A = dglsp.from_csr(indptr, indices, val)
    SparseMatrix(indices=tensor([[0, 1, 2, 2, 2],
                                 [1, 2, 0, 1, 2]]),
                 values=tensor([[1, 1],
                                [2, 2],
                                [3, 3],
                                [4, 4],
                                [5, 5]]),
                 shape=(3, 3), nnz=5, val_size=(2,))
    """
    if shape is None:
        shape = (indptr.shape[0] - 1, torch.max(indices) + 1)
    if val is None:
        val = torch.ones(indices.shape[0]).to(indptr.device)

    return SparseMatrix(
        torch.ops.dgl_sparse.from_csr(indptr, indices, val, shape)
    )


def from_csc(
    indptr: torch.Tensor,
    indices: torch.Tensor,
    val: Optional[torch.Tensor] = None,
    shape: Optional[Tuple[int, int]] = None,
) -> SparseMatrix:
    r"""Creates a sparse matrix from CSC indices.

    For column i of the sparse matrix

    - the row indices of the non-zero elements are stored in
      ``indices[indptr[i]: indptr[i+1]]``
    - the corresponding values are stored in ``val[indptr[i]: indptr[i+1]]``

    Parameters
    ----------
    indptr : torch.Tensor
        Pointer to the row indices of shape N + 1, where N is the
        number of columns
    indices : torch.Tensor
        The row indices of shape nnz
    val : torch.Tensor, optional
        The values of shape (nnz) or (nnz, D). If None, it will be a tensor of
        shape (nnz) filled by 1.
    shape : tuple[int, int], optional
        If not specified, it will be inferred from :attr:`indptr` and
        :attr:`indices`, i.e., (indices.max() + 1, len(indptr) - 1). Otherwise,
        :attr:`shape` should be no smaller than this.

    Returns
    -------
    SparseMatrix
        Sparse matrix

    Examples
    --------

    Case1: Sparse matrix without values

    [[0, 1, 0],
     [0, 0, 1],
     [1, 1, 1]]

    >>> indptr = torch.tensor([0, 1, 3, 5])
    >>> indices = torch.tensor([2, 0, 2, 1, 2])
    >>> A = dglsp.from_csc(indptr, indices)
    SparseMatrix(indices=tensor([[2, 0, 2, 1, 2],
                                 [0, 1, 1, 2, 2]]),
                 values=tensor([1., 1., 1., 1., 1.]),
                 shape=(3, 3), nnz=5)
    >>> # Specify shape
    >>> A = dglsp.from_csc(indptr, indices, shape=(5, 3))
    SparseMatrix(indices=tensor([[2, 0, 2, 1, 2],
                                 [0, 1, 1, 2, 2]]),
                 values=tensor([1., 1., 1., 1., 1.]),
                 shape=(5, 3), nnz=5)

    Case2: Sparse matrix with scalar/vector values. Following example is with
    vector data.

    >>> indptr = torch.tensor([0, 1, 3, 5])
    >>> indices = torch.tensor([2, 0, 2, 1, 2])
    >>> val = torch.tensor([[1, 1], [2, 2], [3, 3], [4, 4], [5, 5]])
    >>> A = dglsp.from_csc(indptr, indices, val)
    SparseMatrix(indices=tensor([[2, 0, 2, 1, 2],
                                 [0, 1, 1, 2, 2]]),
                 values=tensor([[1, 1],
                                [2, 2],
                                [3, 3],
                                [4, 4],
                                [5, 5]]),
                 shape=(3, 3), nnz=5, val_size=(2,))
    """
    if shape is None:
        shape = (torch.max(indices) + 1, indptr.shape[0] - 1)
    if val is None:
        val = torch.ones(indices.shape[0]).to(indptr.device)

    return SparseMatrix(
        torch.ops.dgl_sparse.from_csc(indptr, indices, val, shape)
    )


def val_like(mat: SparseMatrix, val: torch.Tensor) -> SparseMatrix:
    """Creates a sparse matrix from an existing sparse matrix using new values.

    The new sparse matrix will have the same non-zero indices as the given
    sparse matrix and use the given values as the new non-zero values.

    Parameters
    ----------
    mat : SparseMatrix
        An existing sparse matrix with non-zero values
    val : torch.Tensor
        The new values of the non-zero elements, a tensor of shape (nnz) or (nnz, D)

    Returns
    -------
    SparseMatrix
        New sparse matrix

    Examples
    --------

    >>> row = torch.tensor([1, 1, 2])
    >>> col = torch.tensor([2, 4, 3])
    >>> val = torch.ones(3)
    >>> A = dglsp.from_coo(row, col, val)
    >>> A = dglsp.val_like(A, torch.tensor([2, 2, 2]))
    SparseMatrix(indices=tensor([[1, 1, 2],
                                 [2, 4, 3]]),
                 values=tensor([2, 2, 2]),
                 shape=(3, 5), nnz=3)
    """
    return SparseMatrix(torch.ops.dgl_sparse.val_like(mat.c_sparse_matrix, val))


def _sparse_matrix_str(spmat: SparseMatrix) -> str:
    """Internal function for converting a sparse matrix to string
    representation.
    """
    indices_str = str(torch.stack(spmat.coo()))
    values_str = str(spmat.val)
    meta_str = f"shape={spmat.shape}, nnz={spmat.nnz}"
    if spmat.val.dim() > 1:
        val_size = tuple(spmat.val.shape[1:])
        meta_str += f", val_size={val_size}"
    prefix = f"{type(spmat).__name__}("

    def _add_indent(_str, indent):
        lines = _str.split("\n")
        lines = [lines[0]] + [" " * indent + line for line in lines[1:]]
        return "\n".join(lines)

    final_str = (
        "indices="
        + _add_indent(indices_str, len("indices="))
        + ",\n"
        + "values="
        + _add_indent(values_str, len("values="))
        + ",\n"
        + meta_str
        + ")"
    )
    final_str = prefix + _add_indent(final_str, len(prefix))
    return final_str
