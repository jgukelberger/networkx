"""
******
Layout
******

Node positioning algorithms for graph drawing.
"""
#    Copyright (C) 2004-2012 by
#    Aric Hagberg <hagberg@lanl.gov>
#    Dan Schult <dschult@colgate.edu>
#    Pieter Swart <swart@lanl.gov>
#    All rights reserved.
#    BSD license.
import collections
import networkx as nx
__author__ = """Aric Hagberg (hagberg@lanl.gov)\nDan Schult(dschult@colgate.edu)"""
__all__ = ['circular_layout',
           'random_layout',
           'shell_layout',
           'spring_layout',
           'spectral_layout',
           'fruchterman_reingold_layout']

def random_layout(G,dim=2):
    """Position nodes uniformly at random in the unit square.

    For every node, a position is generated by choosing each of dim
    coordinates uniformly at random on the interval [0.0, 1.0).

    NumPy (http://scipy.org) is required for this function.

    Parameters
    ----------
    G : NetworkX graph
       A position will be assigned to every node in G.

    dim : int
       Dimension of layout.

    Returns
    -------
    dict :
       A dictionary of positions keyed by node

    Examples
    --------
    >>> G = nx.lollipop_graph(4, 3)
    >>> pos = nx.random_layout(G)

    """
    try:
        import numpy as np
    except ImportError:
        raise ImportError("random_layout() requires numpy: http://scipy.org/ ")
    n=len(G)
    pos=np.asarray(np.random.random((n,dim)),dtype=np.float32)
    return dict(zip(G,pos))


def circular_layout(G, dim=2, scale=1):
    # dim=2 only
    """Position nodes on a circle.

    Parameters
    ----------
    G : NetworkX graph

    dim : int
       Dimension of layout, currently only dim=2 is supported

    scale : float
        Scale factor for positions

    Returns
    -------
    dict :
       A dictionary of positions keyed by node

    Examples
    --------
    >>> G=nx.path_graph(4)
    >>> pos=nx.circular_layout(G)

    Notes
    ------
    This algorithm currently only works in two dimensions and does not
    try to minimize edge crossings.

    """
    try:
        import numpy as np
    except ImportError:
        raise ImportError("circular_layout() requires numpy: http://scipy.org/ ")
    if len(G)==0:
        return {}
    if len(G)==1:
        return {G.nodes()[0]:(1,)*dim}
    t=np.arange(0,2.0*np.pi,2.0*np.pi/len(G),dtype=np.float32)
    pos=np.transpose(np.array([np.cos(t),np.sin(t)]))
    pos=_rescale_layout(pos,scale=scale)
    return dict(zip(G,pos))

def shell_layout(G,nlist=None,dim=2,scale=1):
    """Position nodes in concentric circles.

    Parameters
    ----------
    G : NetworkX graph

    nlist : list of lists
       List of node lists for each shell.

    dim : int
       Dimension of layout, currently only dim=2 is supported

    scale : float
        Scale factor for positions

    Returns
    -------
    dict :
       A dictionary of positions keyed by node

    Examples
    --------
    >>> G=nx.path_graph(4)
    >>> shells=[[0],[1,2,3]]
    >>> pos=nx.shell_layout(G,shells)

    Notes
    ------
    This algorithm currently only works in two dimensions and does not
    try to minimize edge crossings.

    """
    try:
        import numpy as np
    except ImportError:
        raise ImportError("shell_layout() requires numpy: http://scipy.org/ ")
    if len(G)==0:
        return {}
    if len(G)==1:
        return {G.nodes()[0]:(1,)*dim}
    if nlist==None:
        nlist=[G.nodes()] # draw the whole graph in one shell

    if len(nlist[0])==1:
        radius=0.0 # single node at center
    else:
        radius=1.0 # else start at r=1

    npos={}
    for nodes in nlist:
        t=np.arange(0,2.0*np.pi,2.0*np.pi/len(nodes),dtype=np.float32)
        pos=np.transpose(np.array([radius*np.cos(t),radius*np.sin(t)]))
        npos.update(zip(nodes,pos))
        radius+=1.0

    # FIXME: rescale
    return npos


def fruchterman_reingold_layout(G,dim=2,k=None,
                                pos=None,
                                fixed=None,
                                iterations=50,
                                weight='weight',
                                scale=1.0,
                                grav=None):
    """Position nodes using Fruchterman-Reingold force-directed algorithm. 

    Parameters
    ----------
    G : NetworkX graph

    dim : int
       Dimension of layout

    k : float (default=None)
       Optimal distance between nodes.  If None the distance is set to
       1/sqrt(n) where n is the number of nodes.  Increase this value
       to move nodes farther apart.


    pos : dict or None  optional (default=None)
       Initial positions for nodes as a dictionary with node as keys
       and values as a list or tuple.  If None, then use random initial
       positions.

    fixed : list or None  optional (default=None)
      Nodes to keep fixed at initial position.

    iterations : int  optional (default=50)
       Number of iterations of spring-force relaxation

    weight : string or None   optional (default='weight')
        The edge attribute that holds the numerical value used for
        the edge weight.  If None, then all edge weights are 1.

    scale : float (default=1.0)
        Scale factor for positions. The nodes are positioned 
        in a box of size [0,scale] x [0,scale].  
    
    grav : list or None optional (default=None)
        Gravitational field acting on all nodes.


    Returns
    -------
    dict :
       A dictionary of positions keyed by node

    Examples
    --------
    >>> G=nx.path_graph(4)
    >>> pos=nx.spring_layout(G)

    # The same using longer function name
    >>> pos=nx.fruchterman_reingold_layout(G)
    """
    try:
        import numpy as np
    except ImportError:
        raise ImportError("fruchterman_reingold_layout() requires numpy: http://scipy.org/ ")
    if fixed is not None:
        nfixed=dict(zip(G,range(len(G))))
        fixed=np.asarray([nfixed[v] for v in fixed])

    if pos is not None:
        # Determine size of existing domain to adjust initial positions
        dom_size = max(flatten(pos.values()))
        pos_arr=np.asarray(np.random.random((len(G),dim)))*dom_size
        for i,n in enumerate(G):
            if n in pos:
                pos_arr[i]=np.asarray(pos[n])
    else:
        pos_arr=None

    if grav is not None:
        assert np.shape(grav) == (dim,)
    
    if len(G)==0:
        return {}
    if len(G)==1:
        return {G.nodes()[0]:(1,)*dim}

    try:
        # Sparse matrix
        if len(G) < 500:  # sparse solver for large graphs
            raise ValueError
        A=nx.to_scipy_sparse_matrix(G,weight=weight,dtype='f')
        if k is None and fixed is not None:
           # We must adjust k by domain size for layouts that are not near 1x1
           nnodes,_ = A.shape
           k=dom_size/np.sqrt(nnodes)
        pos=_sparse_fruchterman_reingold(A,dim,k,pos_arr,fixed,iterations,grav)
    except:
        A=nx.to_numpy_matrix(G,weight=weight)
        if k is None and fixed is not None:
           # We must adjust k by domain size for layouts that are not near 1x1
           nnodes,_ = A.shape
           k=dom_size/np.sqrt(nnodes)
        pos=_fruchterman_reingold(A,dim,k,pos_arr,fixed,iterations,grav)
    if fixed is None:
        pos=_rescale_layout(pos,scale=scale)
    return dict(zip(G,pos))

spring_layout=fruchterman_reingold_layout

def _fruchterman_reingold(A, dim=2, k=None, pos=None, fixed=None, 
                          iterations=50,grav=None):
    # Position nodes in adjacency matrix A using Fruchterman-Reingold
    # Entry point for NetworkX graph is fruchterman_reingold_layout()
    try:
        import numpy as np
    except ImportError:
        raise ImportError("_fruchterman_reingold() requires numpy: http://scipy.org/ ")

    try:
        nnodes,_=A.shape
    except AttributeError:
        raise nx.NetworkXError(
            "fruchterman_reingold() takes an adjacency matrix as input")

    A=np.asarray(A) # make sure we have an array instead of a matrix

    if pos is None:
        # random initial positions
        pos=np.asarray(np.random.random((nnodes,dim)),dtype=A.dtype)
    else:
        # make sure positions are of same type as matrix
        pos=pos.astype(A.dtype)
    
    if grav is not None:
        grav = np.asarray(grav,A.dtype)
    
    # optimal distance between nodes
    if k is None:
        k=np.sqrt(1.0/nnodes)
    # the initial "temperature"  is about .1 of domain area (=1x1)
    # this is the largest step allowed in the dynamics.
    # We need to calculate this in case our fixed positions force our domain
    # to be much bigger than 1x1
    t = max(max(pos.T[0]) - min(pos.T[0]), max(pos.T[1]) - min(pos.T[1]))*0.1
    # simple cooling scheme.
    # linearly step down by dt on each iteration so last iteration is size dt.
    dt=t/float(iterations+1)
    delta = np.zeros((pos.shape[0],pos.shape[0],pos.shape[1]),dtype=A.dtype)
    # the inscrutable (but fast) version
    # this is still O(V^2)
    # could use multilevel methods to speed this up significantly
    for iteration in range(iterations):
        # matrix of difference between points
        for i in range(pos.shape[1]):
            delta[:,:,i]= pos[:,i,None]-pos[:,i]
        # distance between points
        distance=np.sqrt((delta**2).sum(axis=-1))
        # enforce minimum distance of 0.01
        distance=np.where(distance<0.01,0.01,distance)
        # displacement "force"
        displacement=np.transpose(np.transpose(delta)*\
                                  (k*k/distance**2-A*distance/k))\
                                  .sum(axis=1)
        # add effect of gravitational field
        if grav is not None:
            displacement += grav
        # update positions
        length=np.sqrt((displacement**2).sum(axis=1))
        length=np.where(length<0.01,0.1,length)
        delta_pos=np.transpose(np.transpose(displacement)*t/length)
        if fixed is not None:
            # don't change positions of fixed nodes
            delta_pos[fixed]=0.0
        pos+=delta_pos
        # cool temperature
        t-=dt
    return pos


def _sparse_fruchterman_reingold(A, dim=2, k=None, pos=None, fixed=None, 
                                 iterations=50, grav=None):
    # Position nodes in adjacency matrix A using Fruchterman-Reingold  
    # Entry point for NetworkX graph is fruchterman_reingold_layout()
    # Sparse version
    try:
        import numpy as np
    except ImportError:
        raise ImportError("_sparse_fruchterman_reingold() requires numpy: http://scipy.org/ ")
    try:
        nnodes,_=A.shape
    except AttributeError:
        raise nx.NetworkXError(
            "fruchterman_reingold() takes an adjacency matrix as input")
    try:
        from scipy.sparse import spdiags,coo_matrix
    except ImportError:
        raise ImportError("_sparse_fruchterman_reingold() scipy numpy: http://scipy.org/ ")
    # make sure we have a LIst of Lists representation
    try:
        A=A.tolil()
    except:
        A=(coo_matrix(A)).tolil()

    if pos==None:
        # random initial positions
        pos=np.asarray(np.random.random((nnodes,dim)),dtype=A.dtype)
    else:
        # make sure positions are of same type as matrix
        pos=pos.astype(A.dtype)

    if grav is not None:
        grav = np.asarray(grav,A.dtype)

    # no fixed nodes
    if fixed==None:
        fixed=[]

    # optimal distance between nodes
    if k is None:
        k=np.sqrt(1.0/nnodes)
    # the initial "temperature"  is about .1 of domain area (=1x1)
    # this is the largest step allowed in the dynamics.
    t=0.1
    # simple cooling scheme.
    # linearly step down by dt on each iteration so last iteration is size dt.
    dt=t/float(iterations+1)

    displacement=np.zeros((dim,nnodes))
    for iteration in range(iterations):
        displacement*=0
        # loop over rows
        for i in range(A.shape[0]):
            if i in fixed:
                continue
            # difference between this row's node position and all others
            delta=(pos[i]-pos).T
            # distance between points
            distance=np.sqrt((delta**2).sum(axis=0))
            # enforce minimum distance of 0.01
            distance=np.where(distance<0.01,0.01,distance)
            # the adjacency matrix row
            Ai=np.asarray(A.getrowview(i).toarray())
            # displacement "force"
            displacement[:,i]+=\
                (delta*(k*k/distance**2-Ai*distance/k)).sum(axis=1)
            # add effect of gravitational field
            if grav is not None:
                displacement[:,i] += grav
        # update positions
        length=np.sqrt((displacement**2).sum(axis=0))
        length=np.where(length<0.01,0.1,length)
        pos+=(displacement*t/length).T
        # cool temperature
        t-=dt
    return pos


def spectral_layout(G, dim=2, weight='weight', scale=1):
    """Position nodes using the eigenvectors of the graph Laplacian. 

    Parameters
    ----------
    G : NetworkX graph

    dim : int
       Dimension of layout

    weight : string or None   optional (default='weight')
        The edge attribute that holds the numerical value used for
        the edge weight.  If None, then all edge weights are 1.

    scale : float
        Scale factor for positions

    Returns
    -------
    dict :
       A dictionary of positions keyed by node

    Examples
    --------
    >>> G=nx.path_graph(4)
    >>> pos=nx.spectral_layout(G)

    Notes
    -----
    Directed graphs will be considered as undirected graphs when
    positioning the nodes.

    For larger graphs (>500 nodes) this will use the SciPy sparse
    eigenvalue solver (ARPACK).
    """
    # handle some special cases that break the eigensolvers
    try:
        import numpy as np
    except ImportError:
        raise ImportError("spectral_layout() requires numpy: http://scipy.org/ ")
    if len(G)<=2:
        if len(G)==0:
            pos=np.array([])
        elif len(G)==1:
            pos=np.array([[1,1]])
        else:
            pos=np.array([[0,0.5],[1,0.5]])
        return dict(zip(G,pos))
    try:
        # Sparse matrix
        if len(G)< 500:  # dense solver is faster for small graphs
            raise ValueError
        A=nx.to_scipy_sparse_matrix(G, weight=weight,dtype='d')
        # Symmetrize directed graphs
        if G.is_directed():
            A=A+np.transpose(A)
        pos=_sparse_spectral(A,dim)
    except (ImportError,ValueError):
        # Dense matrix
        A=nx.to_numpy_matrix(G, weight=weight)
        # Symmetrize directed graphs
        if G.is_directed():
            A=A+np.transpose(A)
        pos=_spectral(A,dim)

    pos=_rescale_layout(pos,scale)
    return dict(zip(G,pos))


def _spectral(A, dim=2):
    # Input adjacency matrix A
    # Uses dense eigenvalue solver from numpy
    try:
        import numpy as np
    except ImportError:
        raise ImportError("spectral_layout() requires numpy: http://scipy.org/ ")
    try:
        nnodes,_=A.shape
    except AttributeError:
        raise nx.NetworkXError(\
            "spectral() takes an adjacency matrix as input")

    # form Laplacian matrix
    # make sure we have an array instead of a matrix
    A=np.asarray(A)
    I=np.identity(nnodes,dtype=A.dtype)
    D=I*np.sum(A,axis=1) # diagonal of degrees
    L=D-A

    eigenvalues,eigenvectors=np.linalg.eig(L)
    # sort and keep smallest nonzero
    index=np.argsort(eigenvalues)[1:dim+1] # 0 index is zero eigenvalue
    return np.real(eigenvectors[:,index])

def _sparse_spectral(A,dim=2):
    # Input adjacency matrix A
    # Uses sparse eigenvalue solver from scipy
    # Could use multilevel methods here, see Koren "On spectral graph drawing"
    try:
        import numpy as np
        from scipy.sparse import spdiags
    except ImportError:
        raise ImportError("_sparse_spectral() requires scipy & numpy: http://scipy.org/ ")
    try:
        from scipy.sparse.linalg.eigen import eigsh
    except ImportError:
        # scipy <0.9.0 names eigsh differently 
        from scipy.sparse.linalg import eigen_symmetric as eigsh
    try:
        nnodes,_=A.shape
    except AttributeError:
        raise nx.NetworkXError(\
            "sparse_spectral() takes an adjacency matrix as input")

    # form Laplacian matrix
    data=np.asarray(A.sum(axis=1).T)
    D=spdiags(data,0,nnodes,nnodes)
    L=D-A

    k=dim+1
    # number of Lanczos vectors for ARPACK solver.What is the right scaling?
    ncv=max(2*k+1,int(np.sqrt(nnodes)))
    # return smallest k eigenvalues and eigenvectors
    eigenvalues,eigenvectors=eigsh(L,k,which='SM',ncv=ncv)
    index=np.argsort(eigenvalues)[1:k] # 0 index is zero eigenvalue
    return np.real(eigenvectors[:,index])


def _rescale_layout(pos,scale=1):
    # rescale to (0,pscale) in all axes

    # shift origin to (0,0)
    lim=0 # max coordinate for all axes
    for i in range(pos.shape[1]):
        pos[:,i]-=pos[:,i].min()
        lim=max(pos[:,i].max(),lim)
    # rescale to (0,scale) in all directions, preserves aspect
    for i in range(pos.shape[1]):
        pos[:,i]*=scale/lim
    return pos


# fixture for nose tests
def setup_module(module):
    from nose import SkipTest
    try:
        import numpy
    except:
        raise SkipTest("NumPy not available")
    try:
        import scipy
    except:
        raise SkipTest("SciPy not available")

def flatten(l):
    try:
        bs = basestring
    except NameError:
        # Py3k
        bs = str
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, bs):
            for sub in flatten(el):
                yield sub
        else:
            yield el

