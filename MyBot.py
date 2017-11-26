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
"""

import hlt
import logging
import time
from enum import Enum

class ActionType(Enum):
    DIVIDE = 0
    FORTIFY = 1
    ATTACK = 2
    DEFEND = 3
    CONQUER = 4
    
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

    def get_id(self):
        return self.ship.id
        
    def do_action(self, game_map, action=ActionType.DIVIDE):
        self.action = action
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
            raise ValueError('Invalid Action Type')
        return cmd
                
    def do_divide_action(self, game_map):
        logging.info("Ship "+str(self.get_id()) + " doing action DIVIDE")
        closest_free_planet = self.find_closest_planet(game_map, planet_status='free')
        if closest_free_planet:
            return self.navigate_then_dock(game_map, closest_free_planet)
        else:
            return ''
        
        
    def do_foritfy_action(self, game_map):
        logging.info("Ship "+str(self.get_id()) + " doing action FORTIFY")
        pass
        
        
    def do_attack_action(self, game_map):
        logging.info("Ship "+str(self.get_id()) + " doing action ATTACK")
        closest_enemy_planet = self.find_closest_planet(game_map, planet_status='enemy')
        if closest_enemy_planet:
            weakest_ship = get_weakest_ship(closest_enemy_planet.all_docked_ships())
        else:
            return ''
        if weakest_ship:
            return self.basic_navigation(game_map,weakest_ship)
        else:
            return ''
        
        
    def do_defend_action(self, game_map):
        logging.info("Ship "+str(self.get_id()) + " doing action DEFEND")
        pass
        
        
    def do_conquer_action(self, game_map):
        logging.info("Ship "+str(self.get_id()) + " doing action CONQUER")
        pass
      
    def basic_navigation(self, game_map, destination):
        nav_cmd = self.ship.navigate(
                self.ship.closest_point_to(destination),
                game_map,
                speed=int(hlt.constants.MAX_SPEED),
                ignore_ships=True)
        if nav_cmd:
            return nav_cmd
        else:
            return ''
          
        
    def navigate_then_dock(self, game_map, planet):    
        if self.ship.can_dock(planet):
            return self.ship.dock(planet)
        else:
            return self.basic_navigation(game_map,planet)
    
        
    def find_closest_planet(self, game_map, planet_status='free'):

        # For each planet in the game (only non-destroyed planets are included)
        best_planet = []
        min_dist = 1000000
        for planet in game_map.all_planets():

            # determine if we are interested in this planet or not
            if planet.is_owned():
                if planet_status == 'free':
                    continue
                else:
                    if planet.owner == game_map.get_me() and planet_status == 'enemy':
                        continue
                    if planet.owner != game_map.get_me() and planet_status == 'mine':
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
    

class SwarmMaster:
    def __init__(self):
        logging.info("Starting Swarm Master")
        self.planets_being_explored = []
        self.active_ship_list = []

            
    def update_ship_list(self, game_map):
        self.active_ship_list = [ActionShip(ship) for ship in game_map.get_me().all_ships() if ship.docking_status == hlt.entity.Ship.DockingStatus.UNDOCKED]


    def update_swarm(self, game_map):
        
        command_queue = []
        self.planets_being_explored = []
        self.update_ship_list(game_map)

        for actionShip in self.active_ship_list:
        
            cmd = actionShip.do_action(game_map,ActionType.DIVIDE)
            if not cmd:
                cmd = actionShip.do_action(game_map,ActionType.ATTACK)
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
        logging.info("Executing Turn: " + str(self.turn_counter))

        commands = self.swarm.update_swarm(self.game.update_map())
        if not commands:
            commands = ''
        logging.info("Commands: "+str(commands))
        self.game.send_command_queue(commands)


if __name__ == "__main__":
    gm = GameMaster()
    while True:
        gm.one_turn()
