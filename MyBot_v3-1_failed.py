"""
Custom halite bot by ABaucom

This bot will use general path planning and swarm tactics to play

Key points
- Use A* planning for all path routes
- Centralized swarm processing (make decisions as a group)
- For first pass, just try to find optimal distribution of ships to take over planets fastest
    - Assume no enemies for now and worry about enemy-based strategies later

Better strategy
- Each ship has a number of actions it can take: divide, fortify, attack, defend, conquer
    - Divide will send the ship to the closest unocupied planet, will superceed another ship 'dividing' to that planet if it is closer (need to be careful of looping here) - also need a flag for sending multiple ships to planets 
    - Foritfy will send the ship to the closest planet we own.
    - Attack will send ships to attack enemies on other planets (aim maybe for weakest enemy on closest planet)
    - Defend will attack enemies in flight
    - Conquer will aim to destroy entire planets by crashing ships into them
- What action to take is determined by some higher level probabalistic process (i.e. NN or game logic)
    -Look at a few global game parameters and then a subset of local entities to choose action
- Once an action is chosen, there is a small probability that this action will be abandoned or if there is a significant change in the game state
- Three tierd approach
    - Strategist looks at game state and determines what percentage of fleet should do which actions
    - Swarm master assigns actions to ships and helps determine best ship for each action
    - Ships carry out actions and communicate with swarm master regarding suitability for action
"""

import hlt
import logging
import time
from enum import Enum
import random

class ActionType(Enum):
    DIVIDE = 0
    FORTIFY = 1
    ATTACK = 2
    DEFEND = 3
    CONQUER = 4
    EVADE = 5
    
def get_weakest_ship(ship_list):

    weakest_ship = []
    lowest_health = 10000000
    for ship in ship_list:
        if ship.health < lowest_health:
            weakest_ship = ship
            lowest_health = ship.health
    return weakest_ship

class ActionShip:

    def __init__(self, ship, default_action=ActionType.DIVIDE):
        self.ship = ship
        self.action = default_action
        self.is_action_set = False

    def get_id(self):
        return self.ship.id
        
    def set_action(self, action):
        self.action = action
        self.is_action_set = True
        logging.info(str(self.ship.id)+": setting action to "+str(action))
        
    def do_action(self, game_map):
            
        if self.action == ActionType.DIVIDE:
            cmd = self.do_divide_action(game_map)
        elif self.action == ActionType.FORTIFY:
            cmd = self.do_fortify_action(game_map)
        elif self.action == ActionType.ATTACK:
            cmd = self.do_attack_action(game_map)
        elif self.action == ActionType.DEFEND:
            cmd = self.do_defend_action(game_map)
        elif self.action == ActionType.CONQUER:
            cmd = self.do_conquer_action(game_map)
        else:
            logging.warning("Invalid ActionType")
            cmd = ''
            
        return cmd
                
    def do_divide_action(self, game_map):
        logging.info("Ship "+str(self.get_id()) + " doing action DIVIDE")
        closest_free_planet = self.find_closest_planet(game_map, planet_status='free')
        if closest_free_planet:
            return self.navigate_then_dock(game_map, closest_free_planet)
        else:
            return ''
           
    def do_fortify_action(self, game_map):
        logging.info("Ship "+str(self.get_id()) + " doing action FORTIFY")
        closest_owned_planet = self.find_closest_planet(game_map, planet_status='mine')
        if closest_owned_planet:
            return self.navigate_then_dock(game_map, closest_owned_planet)
        else:
            return ''
        pass
           
    def do_attack_action(self, game_map):
        logging.info("Ship "+str(self.get_id()) + " doing action ATTACK")
        closest_enemy_planet = self.find_closest_planet(game_map, planet_status='enemy')
        if closest_enemy_planet:
            weakest_ship = get_weakest_ship(closest_enemy_planet.all_docked_ships())
        else:
            return ''
        if weakest_ship:
            return self.basic_navigation(game_map,weakest_ship,ignore_mode='ships')
        else:
            return ''
        
        
    def do_defend_action(self, game_map):
        logging.info("Ship "+str(self.get_id()) + " doing action DEFEND")
        closest_enemy_ship = self.find_closest_enemy_ship(game_map)
        if closest_enemy_ship:
            if self.ship.calculate_distance_between(closest_enemy_ship) < 20:
                return self.basic_navigation(game_map,closest_enemy_ship,ignore_mode='ships')
            else:
                return self.basic_navigation(game_map,closest_enemy_ship,ignore_mode='none')
        
        
    def do_conquer_action(self, game_map):
        logging.info("Ship "+str(self.get_id()) + " doing action CONQUER")
        closest_enemy_planet = self.find_closest_planet(game_map, planet_status='enemy')
        if closest_enemy_planet:
            return self.basic_navigation(game_map,closest_enemy_planet,ignore_mode='planets')
        else:
            return ''
        
      
    def basic_navigation(self, game_map, destination,ignore_mode='none'):
        if ignore_mode == 'none':
            nav_cmd = self.ship.navigate(
                    self.ship.closest_point_to(destination),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED))
        elif ignore_mode == 'ships':
            nav_cmd = self.ship.navigate(
                    self.ship.closest_point_to(destination),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=True)
        elif ignore_mode == 'planets':
            nav_cmd = self.ship.navigate(
                    destination,
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_planets=True)
        elif ignore_mode == 'all':
            nav_cmd = self.ship.navigate(
                    destination,
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    avoid_obstacles=False)
        else:
            logging.warning("Invalid ignore_mode set for basic_navigation")
            nav_cmd = ''
        
        if nav_cmd:
            return nav_cmd
        else:
            return ''
          
        
    def navigate_then_dock(self, game_map, planet):    
        if self.ship.can_dock(planet):
            logging.info(str(self.ship.id)+": Docking!")
            return self.ship.dock(planet)
        else:
            return self.basic_navigation(game_map,planet)
    
    @staticmethod
    def is_planet_suitable(game_map, planet, planet_status, ignore_list=set()):
        
        if planet.is_owned():
            if planet_status == 'free':
                return False
            else:
                if planet.owner == game_map.get_me() and (planet_status == 'enemy' or planet.is_full()):
                    return False
                if planet.owner != game_map.get_me() and planet_status == 'mine':
                    return False
                    
        if planet in ignore_list:
            return False
        
        return True
        
        
    def find_closest_planet(self, game_map, planet_status='free'):

        # For each planet in the game (only non-destroyed planets are included)
        best_planet = []
        min_dist = 1000000
        for planet in game_map.all_planets():

            if not self.is_planet_suitable(game_map, planet, planet_status):
                continue            

            # find distance to planet
            dist = self.ship.calculate_distance_between(planet)
            if dist < min_dist:
                min_dist = dist
                best_planet = planet

        #only update list if we get a valid planet
        if not best_planet:
            return []
        else:
            return best_planet
            
    def find_closest_enemy_ship(self, game_map):

        # For each enemy ship
        best_ship = []
        min_dist = 1000000
        for player in game_map.all_players():
            if player == game_map.get_me():
                continue
            
            for enemy_ship in player.all_ships():          
                # find distance to ship
                dist = self.ship.calculate_distance_between(enemy_ship)
                if dist < min_dist:
                    min_dist = dist
                    best_ship = enemy_ship

        #only update list if we get a valid planet
        if not best_ship:
            return []
        else:
            return best_ship
    

class SwarmMaster:

    DIVIDE_PROB = 0.7
    ATTACK_PROB = 0.7
    

    def __init__(self):
        logging.info("Starting Swarm Master")
        self.planets_being_explored = []
        self.active_ship_list = []

            
    def update_ship_list(self, game_map):
        
        #first check to see if any of my ships have docked or been destroyed 
        my_ship_ids = [ship.id for ship in game_map.get_me().all_ships()]
        logging.info("All ship ids: "+str(my_ship_ids))
        #for actionShip in self.active_ship_list:
            #if actionShip.ship.docking_status != hlt.entity.Ship.DockingStatus.UNDOCKED or actionShip.get_id() not in my_ship_ids:
                #self.active_ship_list.remove(actionShip)
        
        #next, figure out if there are any new ships to add to the active list
        active_ship_ids = [actionShip.get_id() for actionShip in self.active_ship_list]
        logging.info("Active ship ids: "+str(active_ship_ids))
        for ship in game_map.get_me().all_ships():
            if ship.docking_status == hlt.entity.Ship.DockingStatus.UNDOCKED and not ship.id in active_ship_ids:
                self.active_ship_list.append(ActionShip(ship))
      


    def set_ship_action(self, actionShip):
        if random.random() < self.DIVIDE_PROB:
            actionShip.set_action(ActionType.DIVIDE)
        else:
            actionShip.set_action(ActionType.FORTIFY)
            
    def set_ship_offensive_action(self, actionShip):
        if random.random() < self.ATTACK_PROB:
            actionShip.set_action(ActionType.ATTACK)
        else:
            actionShip.set_action(ActionType.DEFEND)
        

    def update_swarm(self, game_map, turn_count, turn_time):
        
        logging.info("Updating swarm")
        command_queue = []
        self.planets_being_explored = []
        self.update_ship_list(game_map)

        for actionShip in self.active_ship_list:
        
            #if we are getting close to time limit, break early
            if time.time() - turn_time > 1.75:
                logging.warning("Breaking from turn "+str(turn_count)+" early due to time limit!")
                break
            
            #set action if it isn't set already
            if not actionShip.is_action_set:
                self.set_ship_offensive_action(actionShip)
        
            cmd = actionShip.do_action(game_map)
            
            #if the set action doesn't work, then try offensive action
            if not cmd:
                self.set_ship_offensive_action(actionShip)
                cmd = actionShip.do_action(game_map)                
               
            command_queue.append(cmd)

        return command_queue


class GameMaster:
    def __init__(self):

        #start up game process
        self.game = hlt.Game("BaucomBot")
        logging.info("Starting Game Master")

        #init game master
        self.turn_counter = 0
        self.turn_timer = time.time()

        #init swarm master
        self.swarm = SwarmMaster()


    def one_turn(self):

        self.turn_counter += 1
        self.turn_timer = time.time()
        logging.info("Starting Turn: " + str(self.turn_counter))

        commands = self.swarm.update_swarm(self.game.update_map(), self.turn_counter, self.turn_timer)
        if not commands:
            commands = ''
        self.game.send_command_queue(commands)
        logging.info("Commands: "+str(commands))
        logging.info("Ending Turn: "+str(self.turn_counter) + ", Elapsed time: " +str(time.time() - self.turn_timer))


if __name__ == "__main__":
    gm = GameMaster()
    while True:
        gm.one_turn()
