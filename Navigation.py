import numpy as np
from queue import PriorityQueue
import math



def next_path_nodes(node,scene,path):
    lst = ((0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1))
    nxt = []
    dims = (len(scene), len(scene[0]))
    for dxy in lst:
        new_node = (node[0]+dxy[0],node[1]+dxy[1])
        if new_node[0] >= dims[0] or new_node[1] >= dims[1] or new_node[0] < 0 or new_node[1] < 0:
            continue
        if not scene[new_node[0]][new_node[1]]:
            nxt.append((new_node,path+[new_node]))
    return nxt

def score_node(node,goal,moves):
    g = len(moves)
    h = math.sqrt((node[0]-goal[0])**2 + (node[1] - goal[1])**2)
    return g+h


def find_path(start, goal, scene):

    # check to make sure it isn't already solved
    if start == goal:
        return []

    #check to make sure goal and start are not on obstacles
    if scene[start[0]][start[1]] == True:
        return None
    if scene[goal[0]][goal[1]] == True:
        return None

    # initialize search queue and explored set
    explored = set(start)
    q = PriorityQueue()
    for node,path in next_path_nodes(start,scene,[start]):
        score = score_node(node,goal,path)
        q.put((score, (node,path)))
        explored.add(node)

    # search until solution is found
    while True:

        # check if queue is empty
        if q.empty():
            return None

        # grab a node from start of queue
        score, (node, path) = q.get()

        # check for solution
        if node == goal:
            return path

        # expand node and append unexplored nodes to queue
        for new_node,new_path in next_path_nodes(node,scene,path):

            if new_node not in explored:
                score = score_node(new_node,goal,new_path)
                q.put((score, (new_node, new_path)))
                explored.add(new_node)