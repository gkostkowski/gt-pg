from collections import defaultdict

from typing import Any, Dict, List, Optional, Tuple, TypeVar, Union

from graph_tool import Edge, Graph as GtGraph, GraphView, Vertex, VertexPropertyMap
from graph_tool.topology import label_components as gt_label_components
import numpy as np

# vertex index or vertex object
VertexRepr = TypeVar("VertexRepr", int, Vertex)

__all__ = [
    "Graph",
]

# TODO rename to PropertyGraph?
class Graph(object):
    """
    Wrapper class for graph-tool Graph instance. Facilitates creation and
    retrieving of graph vertices and edges with key properties.
    Contains method for identifying graph components.
    """

    def __init__(self, gt_graph:'graph_tool.Graph'=None,
        v_id_prop_name: str= None,
        e_id_prop_name:str = None,
    ):
        if gt_graph:
            if not v_id_prop_name or not e_id_prop_name:
                raise ValueError(
                    "When wrapping existed graph, you must specify key property for"
                    "vertex and edge."
                )
            self._g = gt_graph
            self._v_props = self._g.vp.keys()
            self._e_props = self._g.ep.keys()
            self._v_id_prop = v_id_prop_name
            self._e_id_prop = e_id_prop_name
        else:
            self._g = GtGraph()
            self._v_props = None
            self._e_props = None
            self._v_id_prop = None
            self._e_id_prop = None
        self._v_index = {}


    @property
    def graph(self) -> GtGraph:
        return self._g

    @property
    def vertex_properties(self):
        return self.graph.vertex_properties

    @property
    def vp(self):
        return self.vertex_properties

    @property
    def edge_properties(self):
        return self.graph.edge_properties

    @property
    def ep(self):
        return self.edge_properties

    def edge(self, *args, **kwargs):
        return self.graph.edge(*args, **kwargs)

    def save(self, *args, **kwargs):
        return self.graph.save(*args, **kwargs)

    def init_graph(self, v_props: Dict[str, str], e_props: Dict[str, str]) -> None:
        self._v_props = self._get_props_names(v_props)
        self._e_props = self._get_props_names(e_props)
        self._add_properties("v", v_props)
        if e_props:
            self._add_properties("e", e_props)

    def set_vertex_id_prop(self, prop_name: str) -> None:
        """After adding properties, sets property which will be used to identify
        vertex in graph"""
        if not self._v_props:
            raise RuntimeError("Properties for vertex not initialised.")
        if prop_name not in self._v_props:
            raise ValueError(f"Vertex property '{prop_name}' not known")
        self._v_id_prop = prop_name

    def set_edge_id_prop(self, prop_name: str) -> None:
        """After adding properties, sets property which will be used to identify
        edge in graph"""
        if not prop_name:
            return
        if not self._e_props:
            raise RuntimeError("Properties for edge not initialised.")
        if prop_name not in self._e_props:
            raise ValueError(f"Edge property '{prop_name}' not known")
        self._e_id_prop = prop_name

    def create_vertex(self, val: Any) -> Vertex:
        """
        Creates new vertex with specified value for identifying property defined
        for nodes in this graph. Does not check if vertex exists to avoid
        extra computation time; If such checking is needed, then use
        get_create_vertex() method instead.

        Returns:
            created vertex.
        """
        v = self._g.add_vertex()
        self._g.vp[self._v_id_prop][v] = val
        return v

    def create_edge(
        self, v1: VertexRepr, v2: VertexRepr, val: Optional[Any] = None
    ) -> Edge:
        """
        Creates edge between two vertices with specified value (for
        identifying property). Does not check if such edge already exists.
        """
        e = self._g.add_edge(v1, v2)
        if val:
            self._g.ep[self._e_id_prop][e] = val
        return e

    def create_edge_if_not_exists(
        self, v1: VertexRepr, v2: VertexRepr, val: Optional[Any] = None
    ) -> Edge:
        e = self.get_edge(v1, v2, val)
        if not e:
            e = self.create_edge(v1, v2, val)
        return e

    def create_relation(
        self, val1: VertexRepr, val2: VertexRepr, e_val: Optional[Any] = None
    ) -> None:
        """
        Creates relationship composed of source vertex, target vertex and
        edge connecting them. For convinience, method accepts values identifying
        mentioned graph objects (instead of vertex / node objects).
        """
        v1, has_v1 = self.get_create_vertex(val1)
        v2, has_v2 = self.get_create_vertex(val2)
        if has_v1 and has_v2:
            self.create_edge_if_not_exists(v1, v2, e_val)
        else:
            self.create_edge(v1, v2, e_val)

    def get_vertex(self, val: Any, raise_err: bool = False) -> Optional[Vertex]:
        """Returns vertex having specified value for its identifying property."""
        v = self.get_v_by_prop(val, self._v_id_prop)
        if not v and raise_err:
            raise ValueError(
                f"Vertex with value '{val}' for property "
                f"'{self._v_id_prop}' not defined"
            )
        return v

    def get_create_vertex(self, val: Any) -> Vertex:
        """
        Returns pair with vertex having specified value for its identifying
        property. Create such vertex if not exists. Can be used to create vertex
        in graph only if not exists in graph. Second element in pair specifies
        whether vertex existed or not.
        """
        try:
            v = self._v_index[val]
            return v, True
        except KeyError:
            v = self.create_vertex(val)
            self._v_index[val] = v
            return v, False

    def get_v_by_prop(self, val: Any, v_prop: str) -> Optional[Vertex]:
        """Returns vertex from graph which has given value val for
        property v_prop"""
        g = self._g
        # convert to proper data type
        ptype = self._get_v_prop_python_type(v_prop)
        # val = ptype(val)  # not needed if we know that prop is of string type
        for p in g.vertices():
            if g.vp[v_prop][p] == val:
                return p
        return None

    def get_edge(
        self, v1: Union[VertexRepr, str], v2: Union[VertexRepr, str], val: Optional[Any] = None
    ) -> Edge:
        """
        Returns an edge between two vertices. Additionally, matches value for
        identifying property, if given.
        """
        if isinstance(v1, str):
            v1 = self.get_vertex(v1)
        if isinstance(v2, str):
            v2 = self.get_vertex(v2)
        g = self._g
        e = g.edge(v1, v2)
        # FIXME what about many edges between two vertices?
        if val:
            if e and g.ep[self._e_id_prop][e] == val:
                return e
        else:
            return e

    # def get_edge(
    #     self, v1: VertexRepr, v2: VertexRepr, val: Optional[Any] = None
    # ) -> Edge:
    #     """
    #     Returns an edge between two vertices. Additionally, matches value for
    #     identifying property, if given.
    #     """
    #     g = self._g
    #     if val:
    #         edges = g.edge(v1, v2, all_edges=True)
    #         if edges:
    #             for e in edges:
    #                 if val:
    #                     if e and g.ep[self._e_id_prop][e] == val:
    #                         return e
    #     else:
    #         return g.edge(v1, v2)

    def has_edge(
        self,
        v1: Union[int, 'graph_tool.Vertex'],
        v2: Union[int, 'graph_tool.Vertex'],
        vals: Optional[List[str]] = None,
        directed: bool = True,
    ) -> bool:
        """
        Checks whether edge between two vertices (specified by its values) exists
        and whether this edge contains any of passed values. Can check edges
        in both directions.
        """
        if not any(isinstance(v1, t) for t in (int, Vertex)): raise TypeError
        if not any(isinstance(v2, t) for t in (int, Vertex)): raise TypeError
        vals = vals if vals else [None]
        if any(self.get_edge(v1, v2, val) for val in vals):
            return True
        return not directed and any(self.get_edge(v2, v1, val) for val in vals)

    def group_by_vprop(self, vprop: VertexPropertyMap) -> List[GraphView]:
        """
        Groups graph vertices by values in passed vertex property map.

        Args:
            vprop_name (VertexPropertyMap): (external) vertex property map used
                to create Graph views for every distinct value in that map.

        Returns:
            list of lists of vertices; each inner list represents a group.
        """
        comp_dict = defaultdict(list)
        for v in self._g.vertices():
            comp_id = vprop[v]
            comp_dict[comp_id].append(v)
        return comp_dict.values()

    def is_empty(self) -> bool:
        """
        Checks if graph is empty: if it does not contain any vertex.
        """
        return self._g.num_vertices() == 0

    def label_components(self) -> Tuple[VertexPropertyMap, np.array]:
        return gt_label_components(self._g, directed=False)

    def get_vertex_val(self, v: VertexRepr) -> Optional[Any]:
        """
        Returns value of id property for given vertex.
        """
        return self._g.vp[self._v_id_prop][v]

    def _add_properties(self, key_type: str, prop_type: List[str]) -> None:
        """key_type: 'v' or 'e'
        prop_type: list or dict
        """
        if isinstance(prop_type, dict):
            prop_type = prop_type.items()
        for pname, ptype in prop_type:
            if key_type == "v" or key_type == "vertex":
                self._g.vertex_properties[pname] = self._g.new_property(key_type, ptype)
            if key_type == "e" or key_type == "edge":
                self._g.edge_properties[pname] = self._g.new_property(key_type, ptype)

    def _get_props_names(self, props_def: Dict[str, str]) -> Optional[List[str]]:
        if props_def:
            if isinstance(props_def, dict):
                props_def = props_def.items()
            return [p for p, t in props_def]

    def _get_v_prop_python_type(self, prop_name: str) -> Any:
        return self._g.vertex_properties[prop_name].python_value_type()

    def append_vprop_val(self, v_id, vprop, new_vprop_val, create_new_prop=True, array=False):
        """
        Sets vertex property for vertex specified by a value of key property.
        If vertex doesn't exists, it will be created.
        """
        v, _ = self.get_create_vertex(v_id)
        self.set_vprop_val(v, vprop, new_vprop_val, create_new_prop=create_new_prop, array=array)

    def set_vprop_val(self, v, vprop, new_vprop_val, create_new_prop=True, array=False):
        """
        Sets property value (for existed or new property) for existed vertex.
        """
        if vprop not in self._g.vp and create_new_prop:
            self._add_properties('v', {vprop: "string"})
            print(f"Creating new property {vprop}")
        if array:
            self._g.vp[vprop][v].append(new_vprop_val)
        else:
            self._g.vp[vprop][v] = new_vprop_val

    def append_eprop_val(self, v1_id, v2_id, eprop, new_eprop_val, create_new_prop=True):
        e = self.create_edge_if_not_exists(v1_id, v2_id)
        if eprop not in self._g.ep and create_new_prop:
            self._add_properties('e', {eprop: "string"})
            print(f"Creating new property {eprop}")
        self._g.ep[eprop][e] = new_eprop_val

    def remove_dangling_nodes(self):
        """
        Removes existing vertices without any related edge.
        """
        to_remove = [
            v
            for v in self._g.vertices() if v.in_degree() + v.out_degree() == 0
        ]
        self._g.remove_vertex(to_remove)
