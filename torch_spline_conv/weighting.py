import torch
from torch.autograd import Function

from .utils.ffi import weighting_forward as weighting_fw
from .utils.ffi import weighting_backward_src as weighting_bw_src
from .utils.ffi import weighting_backward_weight as weighting_bw_weight
from .utils.ffi import weighting_backward_basis as weighting_bw_basis
from .utils.ffi import weighting_backward as weighting_bw


def weighting_forward(src, weight, basis, weight_index):
    output = src.new(src.size(0), weight.size(2))
    weighting_fw(output, src, weight, basis, weight_index)
    return output


def weighting_backward_src(grad_output, weight, basis, weight_index):
    grad_src = grad_output.new(grad_output.size(0), weight.size(1))
    weighting_bw_src(grad_src, grad_output, weight, basis, weight_index)
    return grad_src


def weighting_backward_weight(grad_output, src, basis, weight_index, K):
    grad_weight = src.new(K, src.size(1), grad_output.size(1))
    weighting_bw_weight(grad_weight, grad_output, src, basis, weight_index)
    return grad_weight


def weighting_backward_basis(grad_output, src, weight, weight_index):
    grad_basis = src.new(weight_index.size())
    weighting_bw_basis(grad_basis, grad_output, src, weight, weight_index)
    return grad_basis


def weighting_backward(grad_output, src, weight, basis, weight_index):
    grad_src = src.new(src.size())
    # grad_weight = weight.new(weight.size())
    grad_weight = weight.new(weight.size(0), weight.size(2), weight.size(1))
    grad_basis = basis.new(basis.size())
    weighting_bw(grad_src, grad_weight, grad_basis, grad_output, src, weight,
                 basis, weight_index)
    return grad_src, grad_weight.transpose(1, 2), grad_basis


class SplineWeighting(Function):
    def __init__(self, weight_index):
        super(SplineWeighting, self).__init__()
        self.weight_index = weight_index

    def forward(self, src, weight, basis):
        self.save_for_backward(src, weight, basis)
        return weighting_forward(src, weight, basis, self.weight_index)

    def backward(self, grad_output):
        grad_src = grad_weight = grad_basis = None
        src, weight, basis = self.saved_tensors

        needs_src, needs_weight, needs_basis = self.needs_input_grad

        if needs_src and needs_weight and needs_basis:
            return weighting_backward(grad_output, src, weight, basis,
                                      self.weight_index)

        if needs_src:
            grad_src = weighting_backward_src(grad_output, weight, basis,
                                              self.weight_index)
        if needs_weight:
            K = weight.size(0)
            grad_weight = weighting_backward_weight(grad_output, src, basis,
                                                    self.weight_index, K)
        if needs_basis:
            grad_basis = weighting_backward_basis(grad_output, src, weight,
                                                  self.weight_index)

        return grad_src, grad_weight, grad_basis


def spline_weighting(src, weight, basis, weight_index):
    if torch.is_tensor(src):
        return weighting_forward(src, weight, basis, weight_index)
    else:
        return SplineWeighting(weight_index)(src, weight, basis)
