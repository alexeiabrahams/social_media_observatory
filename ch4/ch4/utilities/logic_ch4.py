import pandas as pd
import networkx as nx
from networkx.classes.digraph import DiGraph
import community
from deep_translator import GoogleTranslator
from urllib.parse import urlparse
import time

from ..config import handles_queue, messages_queue
from ..utilities.mq_ch4 import send_data_to_queue

from telethon.errors.rpcerrorlist import UsernameInvalidError
from telethon.sync import TelegramClient
from telethon import functions
from telethon.tl.patched import Message as TelegramMessage
from telethon.tl.types.messages import ChatFull

from .db_ch4 import (
    insert_data_into_seed_table,
    insert_data_into_channel_metadata_table_advanced,
    insert_data_into_channel_messages_table_advanced,
    fetch_seed_list_names,
    fetch_seed_list_preview,
    fetch_seed_metadata_full,
    fetch_birth_chart_data,
    fetch_time_series_chart_data,
    fetch_top_messages,
    fetch_weighted_edges_fwd_network,
    fetch_domain_edges,
    fetch_metadata_for_single_channel,
)

SECONDS_TO_PAUSE_BETWEEN_CHANNEL_INFO_LOOKUPS = 30


def extract_data_dictionary_from_channel_object(
    channel_object: ChatFull, channel_name: str
) -> dict:
    return {
        "channel_name": channel_name,
        "channel_id": channel_object.to_dict()["full_chat"]["id"],
        "channel_title": channel_object.to_dict()["chats"][0]["title"],
        "num_subscribers": channel_object.to_dict()["full_chat"]["participants_count"],
        "channel_bio": channel_object.to_dict()["full_chat"]["about"],
        "channel_birthdate": channel_object.to_dict()["chats"][0]["date"],
        "api_response": channel_object.to_json(),
    }


def retrieve_channel_metadata(
    channel_names: list[str], app_name: str, api_id: int, api_hash: str
) -> list[dict]:
    # Retrieve data from Telegram API, using Telethon:
    records = []
    with TelegramClient(app_name, api_id, api_hash) as client:
        for channel_name in channel_names:
            print(f"Querying Telegram API for @{channel_name}...")
            try:
                channel_object = client(
                    functions.channels.GetFullChannelRequest(channel=channel_name)
                )
            except ValueError as e:
                print(e)
                channel_object = None
            except UsernameInvalidError as e:
                print(e)
                channel_object = None
            except Exception as e:
                raise e

            if channel_object is not None:
                records.append(
                    extract_data_dictionary_from_channel_object(
                        channel_object, channel_name
                    )
                )
            else:
                print(f"No metadata returned by Telegram API for @{channel_name}")

            print(
                f"Pausing {SECONDS_TO_PAUSE_BETWEEN_CHANNEL_INFO_LOOKUPS} seconds "
                f"to respect Telegram API rate limits..."
            )
            time.sleep(
                SECONDS_TO_PAUSE_BETWEEN_CHANNEL_INFO_LOOKUPS
            )  # pause to respect API rate limiting

    return records


def retrieve_and_save_channel_metadata(
    channel_names: list[str],
    app_name: str,
    api_id: int,
    api_hash: str,
    seed_list_name: str,
):
    # Retrieve data from Telegram API
    records = retrieve_channel_metadata(channel_names, app_name, api_id, api_hash)

    # Prepare seed data
    seed_records = [
        {
            "channel_name": record["channel_name"],
            "channel_id": record["channel_id"],
            "seed_list": seed_list_name,
        }
        for record in records
    ]

    # Insert data into database
    if len(records) > 0:
        insert_data_into_channel_metadata_table_advanced(records)
        insert_data_into_seed_table(seed_records)


def get_names_of_seed_lists() -> list[dict]:
    return fetch_seed_list_names()


def get_seed_list_preview(my_seed_list_names: list[str]) -> list[dict]:
    return fetch_seed_list_preview(my_seed_list_names)


def get_seed_channel_metadata(seed_list_names: list[str]) -> list[dict]:
    return fetch_seed_metadata_full(seed_list_names)


def get_birth_chart_data(
    birth_chart_unit: str, seed_list_names: list[str]
) -> list[dict]:
    return fetch_birth_chart_data(seed_list_names, birth_chart_unit)


def get_time_series_chart_data(
    start_date: str,
    end_date: str,
    time_series_chart_unit: str,
    seed_list_names: list[str],
) -> list[dict]:
    return fetch_time_series_chart_data(
        seed_list_names, start_date, end_date, time_series_chart_unit
    )


def get_top_messages(
    start_date: str,
    end_date: str,
    seed_list_names: list[str],
    the_limit: int = 1000,
):
    return fetch_top_messages(seed_list_names, start_date, end_date, the_limit)


def generate_markdown_hyperlink(record):
    url = f"https://t.me/{record['channel_name']}/{record['message_id']}"
    return f"[{url}]({url})"


def make_message_table(records: list[dict], seed_list_names: list[str]) -> list[dict]:
    df = pd.DataFrame.from_records(records)

    seed_df = pd.DataFrame.from_records(get_seed_list_preview(seed_list_names))

    df = df.merge(seed_df, on="channel_id", how="left")

    df["url"] = df.apply(lambda x: generate_markdown_hyperlink(x), axis=1)

    df = df[
        [
            "url",
            "message_datetime",
            "message_views",
            "message_forwards",
            "message_text",
            "channel_name",
            "channel_id",
            "message_id",
        ]
    ]

    return df.to_dict("records")


def render_message_table(
    start_date: str, end_date: str, seed_list_names: list[str]
) -> list[dict]:
    df_records = get_top_messages(start_date, end_date, seed_list_names)

    # Create table
    df_records = make_message_table(df_records, seed_list_names)
    return df_records


def translate_messages(df_records: list[dict]) -> list[dict]:
    df = pd.DataFrame.from_records(df_records)

    df["message_translated"] = df["message_text"].apply(
        lambda my_text: GoogleTranslator(source="auto", target="en").translate(my_text)
        if my_text is not None
        else None
    )

    df = df[
        [
            "url",
            "message_datetime",
            "message_views",
            "message_forwards",
            "message_translated",
            "message_text",
            "channel_name",
            "channel_id",
            "message_id",
        ]
    ]

    return df.to_dict("records")


def send_handles_to_tg_channel_metadata_lookup_queue(data_json: dict):
    send_data_to_queue([data_json], handles_queue)


def send_handles_to_tg_channel_messages_lookup_queue(records: list[dict]):
    send_data_to_queue(records, messages_queue)


def store_channel_messages(records: list[dict]):
    insert_data_into_channel_messages_table_advanced(records)


def extract_data_from_message_object(message: TelegramMessage) -> dict:
    message_dict = {
        "channel_id": message.to_dict()["peer_id"]["channel_id"],
        "message_id": message.to_dict()["id"],
        "message_datetime": message.to_dict()["date"],
        "message_views": message.to_dict()["views"],
        "message_forwards": message.to_dict()["forwards"],
        "message_text": message.to_dict()["message"],
        "forwardee_channel_id": None,
        "forwardee_message_id": None,
        "message_is_forward": False,
        "api_response": message.to_json(),
    }

    if message.fwd_from is not None:
        message_dict["message_is_forward"] = True
        if message.to_dict()["fwd_from"]["from_id"] is not None:
            if "channel_id" in message.to_dict()["fwd_from"]["from_id"].keys():
                message_dict["forwardee_channel_id"] = message.to_dict()["fwd_from"][
                    "from_id"
                ]["channel_id"]
                message_dict["forwardee_message_id"] = message.to_dict()["fwd_from"][
                    "channel_post"
                ]

    return message_dict


def retrieve_channel_messages_from_telegram(
    channel_name: str, app_name: str, api_id: int, api_hash: str
) -> list[dict]:
    new_max_id = 0
    messages = []
    with TelegramClient(app_name, api_id, api_hash) as client:
        while True:
            message_iterator = client.iter_messages(
                channel_name, min_id=0, max_id=new_max_id, limit=100
            )

            try:
                new_messages = list(message_iterator)
            except Exception as e:
                print(e)
                new_messages = []

            # Calculate new_max_id
            if len(new_messages) > 0:
                new_max_id = min([message.id for message in new_messages])
                messages += new_messages

                print(
                    f"found {len(messages)} messages so far, and set new_max_id={new_max_id}"
                )

            # Stopping condition
            if len(new_messages) < 100:
                break

            # Respectful pause so as not to flood the API
            time.sleep(1)

    records = [
        extract_data_from_message_object(message)
        for message in messages
        if message.to_dict()["_"] == "Message"
    ]

    return records


def retrieve_and_save_channel_messages(
    channel_name: str, app_name: str, api_id: int, api_hash: str
):
    # Retrieve messages from Telegram API
    records = retrieve_channel_messages_from_telegram(
        channel_name, app_name, api_id, api_hash
    )

    # Save data locally
    store_channel_messages(records)


# def make_cytoscape_stylesheet(my_elements):
#     my_nodes = [elt for elt in my_elements if elt["data"]["type"] == "node"]
#     my_edges = [elt for elt in my_elements if elt["data"]["type"] == "edge"]
#
#     min_node_strength = min([node["data"]["size"] for node in my_nodes])
#     max_node_strength = max([node["data"]["size"] for node in my_nodes])
#     min_edge_weight = min([edge["data"]["weight"] for edge in my_edges])
#     max_edge_weight = max([edge["data"]["weight"] for edge in my_edges])
#
#     my_stylesheet = [
#         {
#             "selector": "node",
#             "style": {
#                 "content": "data(label)",
#                 "color": "black",
#                 "text-valign": "center",
#                 "text-halign": "center",
#                 "width": f"mapData(size, {min_node_strength}, {max_node_strength}, 1, 50)",
#                 "height": f"mapData(size, {min_node_strength}, {max_node_strength}, 1, 50)",
#                 "font-size": f"mapData(size, {min_node_strength}, {max_node_strength}, 1, 50)",
#             },
#         },
#         {
#             "selector": "edge",
#             "style": {
#                 "width": f"mapData(weight, {min_edge_weight}, {max_edge_weight}, 0.1, 5)",
#                 "curve-style": "bezier",
#             },
#         },
#     ]
#
#     my_stylesheet += [
#         {
#             "selector": 'node[id = "{}"]'.format(node["data"]["id"]),
#             "style": {
#                 "opacity": 1,
#                 "background-color": node["data"]["color"],
#             },
#         }
#         for node in my_nodes
#     ]
#
#     my_stylesheet += [
#         {
#             "selector": 'edge[id = "{}"]'.format(edge["data"]["id"]),
#             "style": {
#                 "opacity": 1,
#                 "line-color": edge["data"]["color"],
#             },
#         }
#         for edge in my_edges
#     ]
#
#     return my_stylesheet


def filter_network_by_weight(
    weighted_edges_records: list[dict],
    source_var: str,
    target_var: str,
    weight_var: str,
    network_max_size: int = None,
) -> DiGraph:
    weighted_edges_df = pd.DataFrame.from_records(weighted_edges_records)
    threshold = 0

    def get_num_unique_nodes(weighted_edges_df):
        sources = list(weighted_edges_df[source_var])
        targets = list(weighted_edges_df[target_var])
        return len(list(set(sources + targets)))

    if network_max_size is not None:
        while True:
            weighted_edges_df = weighted_edges_df.loc[
                weighted_edges_df[weight_var] > threshold, :
            ]

            if get_num_unique_nodes(weighted_edges_df) <= network_max_size:
                break

            print(
                f"The graph is too large. Let's filter it down by incrementing the threshold to {threshold}"
            )
            threshold = min(weighted_edges_df[weight_var])

    G = nx.DiGraph()
    G.add_weighted_edges_from(
        weighted_edges_df.loc[:, [source_var, target_var, weight_var]].values,
        weight=weight_var,
    )
    print(f"The graph has {len(G.nodes())} nodes and {len(G.edges())} edges")

    return G


def extract_domain_from_url(my_url):
    try:
        domain = urlparse(my_url).netloc
    except Exception as e:
        if isinstance(e, ValueError):
            domain = None
        else:
            raise e
    return domain


def make_cytoscape_stylesheet(
    my_elements: list[dict], hovered_node: dict = None
) -> list[dict]:
    of_interest_opacity = 1
    not_of_interest_opacity = 0.2

    my_nodes = [elt for elt in my_elements if elt["data"]["type"] == "node"]
    my_edges = [elt for elt in my_elements if elt["data"]["type"] == "edge"]

    min_node_strength = min([node["data"]["size"] for node in my_nodes])
    max_node_strength = max([node["data"]["size"] for node in my_nodes])
    min_edge_weight = min([edge["data"]["weight"] for edge in my_edges])
    max_edge_weight = max([edge["data"]["weight"] for edge in my_edges])

    my_stylesheet = [
        {
            "selector": "node",
            "style": {
                "content": "data(label)",
                "color": "black",
                "text-valign": "center",
                "text-halign": "center",
                "width": f"mapData(size, {min_node_strength}, {max_node_strength}, 1, 50)",
                "height": f"mapData(size, {min_node_strength}, {max_node_strength}, 1, 50)",
                "font-size": f"mapData(size, {min_node_strength}, {max_node_strength}, 1, 50)",
            },
        },
        {
            "selector": "edge",
            "style": {
                "width": f"mapData(weight, {min_edge_weight}, {max_edge_weight}, 0.1, 5)",
                "curve-style": "bezier",
            },
        },
    ]

    if hovered_node is not None:
        edges_of_interest = [
            edge
            for edge in my_edges
            if edge["data"]["source"] == hovered_node["id"]
            or edge["data"]["target"] == hovered_node["id"]
        ]
        node_ids_of_interest = list(
            set(
                [edge["data"]["source"] for edge in edges_of_interest]
                + [edge["data"]["target"] for edge in edges_of_interest]
            )
        )
    else:
        edges_of_interest = my_edges
        node_ids_of_interest = [my_node["data"]["id"] for my_node in my_nodes]

    my_stylesheet += [
        {
            "selector": 'node[id = "{}"]'.format(node["data"]["id"]),
            "style": {
                "opacity": of_interest_opacity
                if node["data"]["id"] in node_ids_of_interest
                else not_of_interest_opacity,
                "background-color": node["data"]["color"],
            },
        }
        for node in my_nodes
    ]

    my_stylesheet += [
        {
            "selector": 'edge[id = "{}"]'.format(edge["data"]["id"]),
            "style": {
                "opacity": of_interest_opacity
                if edge in edges_of_interest
                else not_of_interest_opacity,
                "line-color": edge["data"]["color"],
            },
        }
        for edge in my_edges
    ]

    return my_stylesheet


def map_communities_to_colors(G):
    unique_communities = list(set([G.nodes()[node]["cluster"] for node in G.nodes()]))
    rows = []
    for community in unique_communities:
        num_nodes = len(
            [node for node in G.nodes() if G.nodes()[node]["cluster"] == community]
        )
        rows.append((community, num_nodes))
    df = pd.DataFrame(rows, columns=["cluster", "num_nodes"])
    df.sort_values("num_nodes", ascending=False, inplace=True)
    df.reset_index(inplace=True, drop=True)

    colors = ["red", "blue", "green", "yellow", "purple", "pink", "orange"]

    communities_to_colors = {}
    for i in range(0, df.shape[0]):
        if i < len(colors):
            communities_to_colors[df.loc[i, "cluster"]] = colors[i]
        else:
            communities_to_colors[df.loc[i, "cluster"]] = "grey"

    return communities_to_colors


#########################################################################################


def get_domain_network_edges(
    start_date: str, end_date: str, seed_list_names: list[str]
) -> list[dict]:
    seed_channel_ids = list(
        set([seed["channel_id"] for seed in fetch_seed_list_preview(seed_list_names)])
    )
    df = pd.DataFrame.from_records(
        fetch_domain_edges(seed_channel_ids, start_date, end_date)
    )

    # Extract domains from URLs:
    df["domain"] = df["url"].apply(lambda x: extract_domain_from_url(x))

    # Drop URLs where domain was unextractable:
    df = df.loc[df["domain"].notnull(), :]

    # Drop select domains:
    df = df.loc[~df["domain"].isin(("t.me",)), :]

    # Collapse to unique domains:
    domain_df = df.groupby(["channel_id", "domain"])["weight"].sum()
    domain_df = domain_df.to_frame()
    domain_df = domain_df.reset_index(drop=False)
    domain_df = domain_df.sort_values(["channel_id", "weight"], ascending=[True, False])
    domain_df = domain_df.reset_index(drop=True)

    return domain_df.to_dict("records")


def make_forward_network(
    seed_list_names: list[str],
    start_date: str,
    end_date: str,
    network_max_size: int = None,
) -> DiGraph:
    seed_df = pd.DataFrame.from_records(get_seed_list_preview(seed_list_names))
    weighted_edges_df = pd.DataFrame.from_records(
        fetch_weighted_edges_fwd_network(
            list(seed_df["channel_id"]), start_date, end_date
        )
    )

    G = filter_network_by_weight(
        weighted_edges_df,
        "channel_id",
        "forwardee_channel_id",
        "count_1",
        network_max_size,
    )

    # Set node attributes:
    nx.set_node_attributes(
        G, dict(zip(seed_df["channel_id"], seed_df["channel_name"])), "channel_name"
    )
    nx.set_node_attributes(
        G, dict(zip(seed_df["channel_id"], seed_df["seed_list"])), "seed_list_name"
    )
    nx.set_node_attributes(G, dict(G.in_degree()), "in_degree")
    nx.set_node_attributes(G, dict(G.out_degree()), "out_degree")
    nx.set_node_attributes(G, dict(G.in_degree(weight="count_1")), "in_strength")
    nx.set_node_attributes(G, dict(G.out_degree(weight="count_1")), "out_strength")
    nx.set_node_attributes(G, community.best_partition(G.to_undirected()), "cluster")

    return G


def make_cytoscape_elements(G, weight_var="count_1", label_var="channel_name"):
    community_to_colors_mapper = map_communities_to_colors(G)

    # Create Cytoscape elements:
    my_nodes = [
        {
            "data": {
                "type": "node",
                "id": str(node),
                "label": str(G.nodes()[node][label_var])
                if label_var in G.nodes()[node].keys()
                else "",
                "size": G.nodes()[node]["in_strength"],
                "color": community_to_colors_mapper[G.nodes()[node]["cluster"]],
            }
        }
        for node in G.nodes()
    ]

    my_edges = [
        {
            "data": {
                "type": "edge",
                "id": f"{edge_tuple[0]}-{edge_tuple[1]}",
                "source": str(edge_tuple[0]),
                "target": str(edge_tuple[1]),
                "weight": G.edges()[edge_tuple][weight_var],
                "color": community_to_colors_mapper[
                    G.nodes()[edge_tuple[0]]["cluster"]
                ],
            }
        }
        for edge_tuple in G.edges()
    ]

    my_elements = my_nodes + my_edges  # []  #

    return my_elements


def make_domain_network(
    seed_list_names: list[str],
    start_date: str,
    end_date: str,
    network_max_size: int = None,
):
    domain_records = get_domain_network_edges(start_date, end_date, seed_list_names)

    B = filter_network_by_weight(
        domain_records,
        source_var="channel_id",
        target_var="domain",
        weight_var="weight",
        network_max_size=network_max_size,
    )

    nx.set_node_attributes(B, {node: node for node in B.nodes()}, "label")
    nx.set_node_attributes(B, dict(B.in_degree()), "in_degree")
    nx.set_node_attributes(B, dict(B.out_degree()), "out_degree")
    nx.set_node_attributes(B, dict(B.in_degree(weight="weight")), "in_strength")
    nx.set_node_attributes(B, dict(B.out_degree(weight="weight")), "out_strength")
    nx.set_node_attributes(B, community.best_partition(B.to_undirected()), "cluster")

    return B


def make_domain_table(seed_list_names, start_date, end_date):
    domain_df = pd.DataFrame.from_records(
        get_domain_network_edges(start_date, end_date, seed_list_names)
    )
    domain_df = (
        domain_df.groupby("domain")["weight"]
        .sum()
        .reset_index()
        .sort_values("weight", ascending=False)
    )
    domain_df["domain"] = domain_df["domain"].apply(lambda x: f"[{x}]({x})")
    return domain_df.to_dict("records")


def make_cytoscape_elements_domain_network(B):
    community_to_colors_mapper = map_communities_to_colors(B)

    # Create Cytoscape elements:
    my_nodes = [
        {
            "data": {
                "type": "node",
                "id": node,
                "label": B.nodes()[node]["label"],
                "size": B.nodes()[node]["in_strength"],
                "color": community_to_colors_mapper[B.nodes()[node]["cluster"]],
            }
        }
        for node in B.nodes()
    ]

    my_edges = [
        {
            "data": {
                "type": "edge",
                "id": f"{edge_tuple[0]}-{edge_tuple[1]}",
                "source": edge_tuple[0],
                "target": edge_tuple[1],
                "weight": B.edges()[edge_tuple]["weight"],
                "color": community_to_colors_mapper[
                    B.nodes()[edge_tuple[0]]["cluster"]
                ],
            }
        }
        for edge_tuple in B.edges()
    ]

    my_elements = my_nodes + my_edges

    min_node_strength = min([node["data"]["size"] for node in my_nodes])
    max_node_strength = max([node["data"]["size"] for node in my_nodes])
    min_edge_weight = min([edge["data"]["weight"] for edge in my_edges])
    max_edge_weight = max([edge["data"]["weight"] for edge in my_edges])

    my_stylesheet = [
        {
            "selector": "node",
            "style": {
                "content": "data(label)",
                "color": "black",
                "text-valign": "center",
                "text-halign": "center",
                "width": f"mapData(size, {min_node_strength}, {max_node_strength}, 1, 50)",
                "height": f"mapData(size, {min_node_strength}, {max_node_strength}, 1, 50)",
                "font-size": f"mapData(size, {min_node_strength}, {max_node_strength}, 1, 50)",
            },
        },
        {
            "selector": "edge",
            "style": {
                "width": f"mapData(weight, {min_edge_weight}, {max_edge_weight}, 0.1, 5)",
                "curve-style": "bezier",
            },
        },
    ]

    my_stylesheet += [
        {
            "selector": 'node[id = "{}"]'.format(node["data"]["id"]),
            "style": {
                "opacity": 1,
                "background-color": node["data"]["color"],
            },
        }
        for node in my_nodes
    ]

    my_stylesheet += [
        {
            "selector": 'edge[id = "{}"]'.format(edge["data"]["id"]),
            "style": {
                "opacity": 1,
                "line-color": edge["data"]["color"],
            },
        }
        for edge in my_edges
    ]

    return my_elements, my_stylesheet


def get_metadata_for_single_channel(channel_id):
    return fetch_metadata_for_single_channel(channel_id)
