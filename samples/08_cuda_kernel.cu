// A small CUDA kernel: element-wise SAXPY  y = a*x + y
__global__ void saxpy(int n, float a, const float *x, float *y) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        y[i] = a * x[i] + y[i];
    }
}

// Block-level reduction using shared memory
__global__ void block_sum(const float *in, float *out, int n) {
    __shared__ float buf[256];
    int tid = threadIdx.x;
    int i = blockIdx.x * blockDim.x + tid;
    buf[tid] = (i < n) ? in[i] : 0.0f;
    __syncthreads();
    for (int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s)
            buf[tid] += buf[tid + s];
        __syncthreads();
    }
    if (tid == 0)
        out[blockIdx.x] = buf[0];
}
