"""
This example script demonstrates some simple usage of gt_pg package.
"""

import gt_pg


def main():
    # prepare data for simple graph:
    # prepare names of properties of certain types
    vertex_properties = {
        "uri": "string",
        "label": "string",
    }
    edge_properties = {
        "uri": "string",
        "label": "string",
    }
    
    # prepare values for uris, the keys for vertices and edges
    v_id_prop = "uri"
    e_id_prop = "uri"
    v_uris = ["http://example.com/1", "http://example.com/2", "http://example.com/3"]
    e_uris = ["http://example.com/relA", "http://example.com/relB"]

    # initialize the graph
    g = gt_pg.Graph()
    g.init_graph(
        v_props=vertex_properties,
        e_props=edge_properties,
    )
    g.set_vertex_id_prop(v_id_prop)
    g.set_edge_id_prop(e_id_prop)

    # specify properties for vertices, vertices will be created
    g.append_vprop_val(v_uris[0], "label", "1")
    g.append_vprop_val(v_uris[2], "label", "3")

    # create relation between vertices, non-existing vertices will be created
    g.create_relation(v_uris[0], v_uris[1], e_uris[0])
    g.create_relation(v_uris[2], v_uris[1], e_uris[1])

    # specify property for edge
    g.append_eprop_val(v_uris[2], v_uris[1], "label", "relA")

    # save graph
    g.save('quickstart.graphml')


if __name__ == "__main__":
    main()
