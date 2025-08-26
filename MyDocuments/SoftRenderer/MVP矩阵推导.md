# Model 矩阵

这个要计算的是在 Object 上的某一个点，以世界坐标 origin 为中心，经过缩放以及平移后所在的位置

# View 矩阵

这个实际上要计算的是在 Object 上的某一个点，他在 Camera 的局部坐标系中，应该是什么坐标，本质就是问，这个点相对于 Camera 的位置是多少。
那么这个东西其实是有一个非常明了的公式：

$ \mathbf{p} = \mathbf{p}_{camera} + \mathbf{p}' $

其中，$ \mathbf{p} $ 是那个点在世界坐标系中的位置，$ \mathbf{p}_{camera} $ 是 Camera 在世界坐标系中的位置，$ \mathbf{p}' $ 是那个点相对于 Camera 的位置。相对于 Camera 的位置 其实就是算这个点 在 Camera 的坐标系中，他的投影分量是多少，假设这个投影分量是 
$
\begin{bmatrix}
x' \\
y' \\
z'
\end{bmatrix}
$
，然后 Camera 的基底是 { $ e_1', e_2', e_3' $ }
，那么有下面的等式

$ \mathbf{p}' =  
\begin{bmatrix}
\,|\, & \,|\, & \,|\, \\
e_1' & e_2' & e_3'\\
\,|\, & \,|\ & \,|\,
\end{bmatrix}
\begin{bmatrix}
x' \\
y' \\
z'
\end{bmatrix}
$

那么，要求
$
\begin{bmatrix}
x' \\
y' \\
z'
\end{bmatrix}
$
就会很简单了，直接反推即可


$ \begin{bmatrix}
\,|\, & \,|\, & \,|\, \\
e_1' & e_2' & e_3'\\
\,|\, & \,|\ & \,|\,
\end{bmatrix}^{-1}(\mathbf{p} - \mathbf{p}_{camera}) = \begin{bmatrix}
x' \\
y' \\
z'
\end{bmatrix}  $

其中，因为{ $ e_1', e_2', e_3' $ } 基底互相垂直，所以 
$\begin{bmatrix}
\,|\, & \,|\, & \,|\, \\
e_1' & e_2' & e_3'\\
\,|\, & \,|\ & \,|\,
\end{bmatrix}$  是个正交矩阵，他的逆矩阵是 
$\begin{bmatrix}
\,-\, & \,e_1'\, & \,-\, \\
\,-\ & e_2' & -\\
\,-\, & \,e_3'\ & \,-\,
\end{bmatrix}$ 

因此，求取这个 View Matrix 是很简单的，只需要 Camera 的 Position，以及 Camera 的基底，而 Camera 的基底，一般都是通过 LookDir 以及 Camera 的 Right 来算出来，这里不再赘述，算出基底后，就能拼出那个逆矩阵，有了逆矩阵，还没结束，我们知道 $(\mathbf{p} - \mathbf{p}_{camera}) $ 其实就是一个位移分量，把这个位移分量再拼上前面的3x3逆矩阵，就能得到一个完整4x4齐次矩阵。也就是

$\begin{bmatrix}
\,-\, & \,e_1'\, & \,-\, & \,-C_{x}\,\\
\,-\ & e_2' & -& \,-C_{y}\,\\
\,-\, & \,e_3'\ & \,-\,& \,-C_{z}\,\\
\,0\, & \,0\ & \,0\,& \,1\,\\
\end{bmatrix}$ 
$C$ 表示 Camera 的 Position 
