import numpy as np
from Queue import PriorityQueue
import math

class PlanningMap:

    def __init__(self,width,height,inflation_buffer=0.5):
        self.width = width
        self.height = height
        self.map = np.zeros((self.height,self.width),dtype=bool)
        self.inflation_buffer = inflation_buffer
        self.ship_for_map_set = -1
        
    def set_obstacle(self,xCenter,yCenter,radius,clear=False,inflation_buffer=True):
        if inflation_buffer:
            radius = radius + self.inflation_buffer
            
        radius = int(math.ceil(radius))
        for x in range(xCenter-radius,xCenter+1):
            for y in range(yCenter-radius,yCenter+1):
                if ((x - xCenter)*(x - xCenter) + (y - yCenter)*(y - yCenter) <= radius*radius):
                    xSym = xCenter - (x - xCenter)
                    ySym = yCenter - (y - yCenter)
                    for x_obs, y_obs in [(x, y), (x, ySym), (xSym , y), (xSym, ySym)]:
                        if self.is_in_map(x_obs,y_obs):
                            if clear:
                                self.map[y_obs,x_obs] = 0
                            else:
                                self.map[y_obs,x_obs] = 1
                        
    def is_in_map(self,x,y):
        if x >= 0 and y >= 0 and x < self.width and y < self.height:
            return True
        else:
            return False
            
    def add_entity_obstacles(self,entity_list):
        for entity in entity_list:
            self.set_obstacle(entity.x,entity.y,entity.radius)
            
    def add_ship_obstacles(self,game_map):
        for player in game_map.all_players():
            ship_list = [ship for ship in player.all_ships()]
            self.add_entity_obstacles(ship_list)
            
    def add_planet_obstacles(self,game_map):
        planet_list = [planet for planet in game_map.all_planets()]
        self.add_entity_obstacles(planet_list)
        
    def add_all_obstalces(self,game_map):
        self.add_ship_obstacles(game_map)
        self.add_planet_obstalces(game_map)
        
    def get_map(self):
        self.reset_map_for_ship() 
        return self.map
        
    def get_map_for_ship(self,ship):
        self.reset_map_for_ship() 
        self.set_obstacle(ship.x,ship.y,ship.radius,clear=True)
        self.ship_for_map_set = ship
        return self.map
        
    def reset_map_for_ship(self):
        if self.ship_for_map_set != -1:
            self.set_obstacle(self.ship_for_map_set.x,self.ship_for_map_set.y,self.ship_for_map_set.radius,clear=False)
            self.ship_for_map_set = -1
    
        
        
        


class PathPlanner:

    def __init__(self, game_map):
        pass
        
    
        


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
  
  
class TestShip:
    def __init__(self,x,y,r):
        self.x = x
        self.y = y
        self.radius = r              
        
                
                
if __name__ == "__main__":
    pm = PlanningMap(10,10)
    s = TestShip(3,3,0.5)
    pm.set_obstacle(5,2,2)
    print(pm.get_map_for_ship(s))
    print(pm.get_map())




