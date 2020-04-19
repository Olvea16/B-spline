import numpy as np

import knot_generators as kg

# The implementation of this B-spline-based camera model is based on the description in the 
# article "Generalized B-spline Camera Model" by Johannes Beck and Christoph Stiller.

# Resources:
# Wikipedia article on b-splines: https://en.wikipedia.org/wiki/B-spline
# Notes of how to construct b-splines: https://pages.mtu.edu/~shene/COURSES/cs3621/NOTES/surface/bspline-construct.html

class CentralModel:
    def __init__(self, image_dimensions, grid_dimensions, control_points, order, knot_method = 'open_uniform', min_basis_value=0.001, end_divergence = 1e-10):
        """Initializes a CentralModel object. \n

        Keyword arguments: \n
        image_dimensions: tuple containing (width, height) of image in pixels. \n
        grid_dimensions: tuple containing (width, height) of grid in pixels. \n
        grid: numpy 3d array containing unit vectors describing camera intrinsics.\n
        order: the order of the interpolation.\n
        min_basis_value: the minimum basis value 
        """
        assert knot_method in ['open_uniform', 'uniform'], 'knot method should be one of the implemented methods.'
        assert isinstance(image_dimensions, tuple) and len(image_dimensions) == 2, 'image_dimensions must be a 2-dimensional tuple.'
        assert isinstance(grid_dimensions, tuple) and len(grid_dimensions) == 2, 'grid_dimensions must be a 2-dimensional tuple.'
        assert isinstance(control_points, np.ndarray) and len(control_points.shape) == 3 and control_points.shape[-1] == 3, 'grid must be a 3-dimensional numpy array with a depth of 3.'
        assert control_points.shape[0] > order and control_points.shape[1] > order, 'order must be smaller than grid size.'

        self.image_width = image_dimensions[0]
        self.image_height = image_dimensions[1]

        self.grid_width = grid_dimensions[0]
        self.grid_height = grid_dimensions[1]

        self.n = control_points.shape[0]
        self.m = control_points.shape[1]

        self.a = control_points

        self.order = order

        if knot_method == 'open_uniform':
            self.th = kg.open_uniform(self.n, order)
            self.tv = kg.open_uniform(self.m, order)

        if knot_method == 'uniform':
            self.th = kg.uniform(self.n, order)
            self.tv = kg.uniform(self.m, order)

        self.min_basis_value = min_basis_value

    def __B__(self, i, k, t, x):
        """Used to calculate the basis function \n

        Keyword arguments: \n
        i: Index for which to sample grid. \n
        k: Basis function order. \n
        t: Knot vector. \n
        x: Pixel coordinate of sample.   
        """
        # Equation 2
        if k == 0:
            if t[i] <= x < t[i + 1]:
                return 1
            else:
                return 0
        
        # Equation 3
        term1a = x - t[i]
        term1b = t[i + k] - t[i]
        term1c = self.__B__(i, k - 1, t, x)

        # If term1b is zero, the division will be undefined.
        # 'Solution' suggested in https://en.wikipedia.org/wiki/Talk%3AB-spline#Avoiding_division_by_zero
        if term1b == 0:
            term1a = term1b = 1

        term2a = t[i + k + 1] - x
        term2b = t[i + k + 1] - t[i + 1]
        term2c = self.__B__(i + 1, k - 1, t, x)

        # If term2b is zero, the division will be undefined.
        if term2b == 0:
            term2a = term2b = 1
        
        return term1a/term1b * term1c + term2a/term2b * term2c

    def sample(self, u, v):
        """Used to sample the b-spline surface. \n

        Keyword arguments: \n
        u: Horizontal pixel coordinate of sample. \n
        v: Vertical pixel coordinate of sample. 
        """
        u += (self.grid_width - self.image_width) / 2
        u /= self.grid_width - 1

        v += (self.grid_height - self.image_height) / 2
        v /= self.grid_height - 1

        Bh = np.array([self.__B__(i, self.order, self.tv, u) for i in range(self.n)])
        Bv = np.array([self.__B__(j, self.order, self.th, v) for j in range(self.m)])

        # Optimization
        vi = np.where(Bh >= self.min_basis_value)[0]
        vj = np.where(Bv >= self.min_basis_value)[0]

        res = np.full((3,), 0.0)
        for i in vi:
            for j in vj:
                aij = self.a[i, j]
                res += np.multiply(aij, Bh[i] * Bv[j])

        return res
    
    def sample_normalized(self, u, v):
        """Used to sample the b-spline surface. Returns a normalized direction. \n

        Keyword arguments: \n
        u: Horizontal pixel coordinate of sample. \n
        v: Vertical pixel coordinate of sample. 
        """
        s = self.sample(u, v)
        return s / np.linalg.norm(s)

    # TODO: Sample with vector of points.

    def sample_grid(self):
        xs = np.floor((self.grid_width - 1) / (self.n - 1) * np.arange(0, self.n))
        ys = np.floor((self.grid_height - 1) / (self.m - 1) * np.arange(0, self.m))

        pts = np.transpose(np.meshgrid(xs, ys))

        samples = np.ndarray((self.n, self.m, 3))
        for i in range(0, self.n):
            for j in range(0, self.m):
                samples[i,j] = self.sample(pts[i,j,0], pts[i,j,1])

        return samples
pass