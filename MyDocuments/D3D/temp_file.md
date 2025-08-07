1. 一个geo，需要一个 gpu buffer 以及 一个 upload buffer，data在给完upload buffer后其实就可以不用保留了，后面可以考虑下如何弄掉这个 upload buffer
除非，这个 geo 经常会改变顶点数据，一般是不会的，如果要改变顶点数据，一般是通过各种shader来改变，比如你通过图元阶段，把 vertex 偏移一段采样的数据，比如地形

2. commandlists，这个需要一个allocator，allocator什么时候该reset这个我们要去考虑下，最好就是设计一个环形缓冲，gpu如果超过了时间就等待fence，所以需要设计一个 frame commands 的数据结构，
让你能通过多个渲染线程（或者计算线程），每个线程自带一个 frame ring buffer，
最后弄一个提交的thread，收集所有线程的 command list ，一起 execute


3. 根签名需要什么，首先是一个 root parameters，是一个数组，声明shader中用到多少类型的全局变量，注意是类型，同一类的全局变量归类到一个 parameter 里面去。
然后一个 parameter 对应一个 descriptor range，一个range 包含多个descriptor，一个descriptor代表一个变量。前面我们提到尽量是一个类型的变量都放到一个range里面，但是range是线性的，
也就是 range 只能是放 0, 1, ..这样放，如果你同一个类型的，比如 D3D12_DESCRIPTOR_RANGE_TYPE_CBV ，但是一个变量是 b0， 一个变量是 b4，那么这个就不连续了



win initialize


dxgi initialize
1. create factory
2. create device， create fence
3. create command objects， create swap chain， create rtv and depth stential view （dsv） heap
4. 
