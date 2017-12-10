import numpy as np
from Queue import PriorityQueue
import math
from enum import Enum
import copy
import bresenham

MAX_SPEED = 7

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
        
    def add_all_obstacles(self,game_map):
        self.add_ship_obstacles(game_map)
        self.add_planet_obstacles(game_map)
        
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
    
        
        
        
class PlanObstacleType(Enum):
    NONE = 0
    PLANETS_ONLY = 1
    SHIPS_ONLY = 2
    ALL = 3

class PathPlanner:
#Everything is flipped with rows and columns for x and y 
 
    def __init__(self, game_map):
        self.full_map = PlanningMap(game_map.width, game_map.height)
        self.full_map.add_all_obstacles(game_map)
        self.empty_map = PlanningMap(game_map.width, game_map.height)
        self.planet_only_map = []
        self.ship_only_map = []
        self.game_map = game_map
        
    def get_nav_cmd_for_ship(self,ship,destination,obstacle_type=PlanObstacleType.ALL):

        path = self.plan_path_for_ship(ship,destination,obstacle_type)
        #print('Path')
        #print(path)
        simple_path = self.simplify_path(ship,path,obstacle_type)
        #print('Simple path')
        #print(simple_path)
        dist,ang = self.path_to_nav_cmd(simple_path)
        #print('Nav cmd')
        #print(dist)
        #print(ang*180/math.pi)
        return ship.thrust(dist,ang)
        
    def simplify_path(self,ship,path,obstacle_type):

        ship_map = self.get_map_for_ship_and_obstacle(ship,obstacle_type)
        return self.find_longest_line(path,ship_map)
        
    def find_longest_line(self, path,grid):
        start_point = path[0]
        
        for cell in path:
            if cell == start_point:
                continue
                
            if self.does_line_intersect(start_point, cell, grid):
                break
            else:
                end_point = cell
                
        return (start_point, end_point)
            
    def does_line_intersect(self, p1,p2,grid):
        
        b = bresenham.bresenham(p1,p2)
        cell_hits = b.path
        intersections = [grid[pt[1]][pt[0]] for pt in cell_hits]
        return np.any(intersections)            
        
        
    def path_to_nav_cmd(self, simple_path):
        x1 = simple_path[0][0]
        y1 = simple_path[0][1]
        x2 = simple_path[1][0]
        y2 = simple_path[1][1]
        
        dist = math.sqrt((x2-x1)**2 + (y2-y1)**2)  
        ang = -math.atan2((y2-y1),(x2-x1)) #negative b/c y axis is flipped
        if dist > MAX_SPEED:
            dist = MAX_SPEED
        
        return dist,ang      
     
     
    def get_map_for_ship_and_obstacle(self, ship, obstacle_type):
        if obstacle_type == PlanObstacleType.NONE:
            return self.empty_map.get_map()
            
        elif obstacle_type == PlanObstacleType.PLANETS_ONLY:
            if not self.planet_only_map:
                self.planet_only_map = PlanningMap(self.game_map.width, self.game_map.height)
                self.planet_only_map.add_planet_obstacles(self.game_map)
            return self.planet_only_map.get_map_for_ship(ship)
            
        elif obstacle_type == PlanObstacleType.SHIPS_ONLY:
            if not self.ship_only_map:
                self.ship_only_map = PlanningMap(self.game_map.width, self.game_map.height)
                self.ship_only_map.add_ship_obstacles(self.game_map)
            return self.ship_only_map.get_map_for_ship(ship)
            
        elif obstacle_type == PlanObstacleType.ALL:
            return self.full_map.get_map_for_ship(ship)
            
        else:
            raise ValueError("Invalide PlanObstacle type") 
         
        
    def plan_path_for_ship(self,ship,destination,obstacle_type):
        
        ship_map = self.get_map_for_ship_and_obstacle(ship,obstacle_type)
        return self.find_path((ship.x,ship.y),destination,ship_map)
  
    def next_path_nodes(self,node,scene,path):
        lst = ((0,1),(1,0),(0,-1),(-1,0))
        nxt = []
        dims = (len(scene[0]), len(scene))
        for dxy in lst:
            new_node = (node[0]+dxy[0],node[1]+dxy[1])
            if new_node[0] >= dims[0] or new_node[1] >= dims[1] or new_node[0] < 0 or new_node[1] < 0:
                continue
            if not scene[new_node[1]][new_node[0]]:
                nxt.append((new_node,path+[new_node]))
        return nxt

    def score_node(self,node,goal,moves):
        g = len(moves)
        h = math.sqrt((node[0]-goal[0])**2 + (node[1] - goal[1])**2)
        return g+h

    def find_path(self,start, goal, scene):

        # check to make sure it isn't already solved
        if start == goal:
            return []

        #check to make sure goal and start are not on obstacles
        if scene[start[1]][start[0]] == True:
            print('Start on obstacle')
            return None
        if scene[goal[1]][goal[0]] == True:
            print('Goal on obstacle')
            print(scene)
            return None

        # initialize search queue and explored set
        explored = set(start)
        q = PriorityQueue()
        for node,path in self.next_path_nodes(start,scene,[start]):
            score = self.score_node(node,goal,path)
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
            for new_node,new_path in self.next_path_nodes(node,scene,path):

                if new_node not in explored:
                    score = self.score_node(new_node,goal,new_path)
                    q.put((score, (new_node, new_path)))
                    explored.add(new_node)
  
  
class TestShip:
    def __init__(self,x,y,r):
        self.x = x
        self.y = y
        self.radius = r 
        self.id = 1  
        
    def thrust(self, magnitude, angle):
        return "t {} {} {}".format(self.id, int(magnitude), round(angle))           
 
class TestPlanet:
    def __init__(self,x,y,r):
        self.x = x
        self.y = y
        self.radius = r
        
class TestMap:
    def __init__(self,w,h):
        self.width = w
        self.height = h
        self.planets = []
        self.players = [TestPlayer()]
        self.planets.append(TestPlanet(2,2,1))
        self.planets.append(TestPlanet(9,6,1))
     
    def get_me(self):
        return self.players[0]
        
    def all_players(self):
        return self.players
        
    def all_planets(self):
        return self.planets
        
class TestPlayer:
    def __init__(self):
        self.id = 1
        self.ships = []
        self.ships.append(TestShip(7,5,0.5))
        self.ships.append(TestShip(5,4,0.5))   
        
    def all_ships(self):
        return self.ships     
                
                
if __name__ == "__main__":
    #pm = PlanningMap(10,10)
    #s = TestShip(3,3,0.5)
    #pm.set_obstacle(5,2,2)
    #print(pm.get_map_for_ship(s))
    #print(pm.get_map())


    m = TestMap(12,10)
    p = PathPlanner(m)
    print(p.full_map.get_map())
    s = m.get_me().all_ships()[0]
    d = (3,6)
    p.get_nav_cmd_for_ship(s,d,PlanObstacleType.ALL)


