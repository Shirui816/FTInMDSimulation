from numba import guvectorize
from numba import float64
import numpy as np

@guvectorize([(float64[:, :], float64[:, :], float64[:, :])], '(n,p),(p,m)->(n,m)',
             target='parallel')  # target='cpu','gpu'
def batch_dot(a, b, ret):  # much more faster than np.tensordot or np.einsum
    r"""Vectorized universal function.
    :param a: np.ndarray, (...,N,P)
    :param b: np.ndarray, (...,P,M)
    axes will be assigned automatically to last 2 axes due to the signatures.
    :param ret: np.ndarray, results. (...,N,M)
    :return: np.ndarray ret.
    """
    for i in range(ret.shape[0]):
        for j in range(ret.shape[1]):
            tmp = 0.
            for k in range(a.shape[1]):
                tmp += a[i, k] * b[k, j]
	ret[i, j] = tmp

def pbc(r, d):
    return r - d * np.round(r/d)

def batchRgTensor(samples, boxes):
    # samples: (..., n_chains, n_monomers, n_dimension)
    # boxes: (..., n_dimension)
    # samples can be (n_batch, n_frame, n_chains, n_monomers, n_dimension) for example
    # or just simply be (n_chains, n_monomers, n_dimension)
    # if there was no batch or frame data, or box is constant of all the simulations
    # boxes = (n_dimension,) would be fine.
    # if boxes were given as (n_batch, n_frame, n_dimension), it must be expand to
    # (n_batch, n_frame, 1, 1, n_dimension) so that for all chains in same frame of
    # one batch of datas, the box is same.
    # same if the samples were given as (n_frames, n_chains, n_monomers, n_dimension)
    # boxes is (n_frames, n_dimension) and must be expand to (n_frames, 1, 1, n_dimension)
    # so that for all chains in same frame has same box lengths.
    
    if boxes.ndim != 1 and samples.ndim <= 3:
        raise ValueError("NO~~~")
    if boxes.ndim < samples.ndim:
        boxes = np.expand_dims(np.expand_dims(boxes, -2), -3)
    chain_length = samples.shape[-2]
    samples = pbc(np.diff(samples, axis=-2), boxes).cumsum(axis=-2) # samples -> (..., n_chains, n-1 monomers, n_dim)
    com = np.expand_dims(samples.sum(axis=-2)/chain_length, -2) # com -> (..., n_chains, 1, n_dim)
    samples = np.append(-com, samples-com, axis=-2) # samples - com of rest n-1 monomers and -com for the 1st monomer
    rgTensors = batch_dot(np.swapaxes(samples, -2, -1), samples) / chain_length
    # batch_dot == np.einsum('...mp,...pn->...mn', np.swapaxes(samples, -2, -1), samples) -> (..., n_chains, n_dim, n_dim)
    # batch_dot == np.einsum('...mp,...pn->...mn', (..., n_chains, n_dim, n_monomers),  (..., n_chains, n_monomers, n_dim))
    # batch_dot is way more faster than np.einsum 
    return np.linalg.eigh(rgTensors) # work on last (..., M, M) matrices
    
