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
- What action to take is determined by some higher level probabalistic process (i.e. NN or game logic)
    -Look at a few global game parameters and then a subset of local entities to choose action
- Once an action is chosen, there is a small probability that this action will be abandoned or if there is a significant change in the game state
"""

import hlt
import logging
import numpy as np
import time


class ActionShip:

    def __init__(self, ship):
        self.ship = ship
        self.action =

    def get_id(self):
        return self.ship.id

    def set_action(self, action):
        self.action = action





class SwarmMaster:
    def __init__(self, game_map, track_enemies):
        logging.info("Starting Swarm Master")
        self.static_map = np.zeros((game_map.width, game_map.height), dtype=bool)
        self.track_enemies = track_enemies
        self.planets_being_explored = []

    def find_closest_planet(self, game_map, ship, planet_status='free'):

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
            dist = ship.calculate_distance_between(planet)

            # only add planets that someone else isn't checking
            if dist < min_dist and planet not in self.planets_being_explored:
                min_dist = dist
                best_planet = planet

        #only update list if we get a valid planet
        if not best_planet:
            return []
        else:
            if planet_status != 'enemy':
                self.planets_being_explored.append(best_planet)
            return best_planet

    def act_on_planet(self, planet, ship, game_map):

        if ship.can_dock(planet):
            # We add the command by appending it to the command_queue
            return ship.dock(planet)
        else:
            # If we can't dock, we move towards the closest empty point near this planet (by using closest_point_to)
            # with constant speed. Don't worry about pathfinding for now, as the command will do it for you.
            # We run this navigate command each turn until we arrive to get the latest move.
            # Here we move at half our maximum speed to better control the ships
            # In order to execute faster we also choose to ignore ship collision calculations during navigation.
            # This will mean that you have a higher probability of crashing into ships, but it also means you will
            # make move decisions much quicker. As your skill progresses and your moves turn more optimal you may
            # wish to turn that option off.
            navigate_command = ship.navigate(
                ship.closest_point_to(planet),
                game_map,
                speed=int(hlt.constants.MAX_SPEED),
                ignore_ships=True)
            # If the move is possible, add it to the command_queue (if there are too many obstacles on the way
            # or we are trapped (or we reached our destination!), navigate_command will return null;
            # don't fret though, we can run the command again the next turn)
            if navigate_command:
                return navigate_command
            else:
                return []

    def attack_enemy_planet(self, ship, enemy_planet, game_map):
        enemy_ships = enemy_planet.all_docked_ships()
        navigate_command = ship.navigate(
            ship.closest_point_to(enemy_ships[0]),
            game_map,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=True)
        if navigate_command:
            return navigate_command
        else:
            return []



    def update_swarm(self, game_map):
        command_queue = []

        self.planets_being_explored = []
        # For every ship that I control
        for ship in game_map.get_me().all_ships():
            # If the ship is docked
            if ship.docking_status != ship.DockingStatus.UNDOCKED:
                # Skip this ship
                continue

            closest_free_planet = self.find_closest_planet(game_map, ship, planet_status='free')

            if closest_free_planet:
                cmd = self.act_on_planet(closest_free_planet,ship,game_map)
                if cmd:
                    command_queue.append(cmd)
            else:
                #if no free planet is available find nearest enemy planet
                closest_enemy_planet = self.find_closest_planet(game_map, ship, planet_status='enemy')
                if closest_enemy_planet:
                    cmd = self.attack_enemy_planet(ship, closest_enemy_planet, game_map)
                    if cmd:
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
        self.swarm = SwarmMaster(self.game.map, track_enemies=False)


    def one_turn(self):

        self.turn_counter += 1
        logging.info("Executing Turn: " + str(self.turn_counter))

        commands = self.swarm.update_swarm(self.game.update_map())
        self.game.send_command_queue(commands)


if __name__ == "__main__":
    gm = GameMaster()
    while True:
        gm.one_turn()
