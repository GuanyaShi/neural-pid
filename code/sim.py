
# standard package
import torch
import gym 
from numpy import identity, zeros, array, vstack, pi
import argparse

# my package
import plotter 
from systems import CartPole
from param import param 
from learning import PlainPID

def main(visualize):

	def run_sim(controller, initial_state):
		states = zeros((len(times), env.n))
		actions = zeros((len(times) - 1, env.m))
		states[0] = env.reset(initial_state)
		reward = 0 
		for step, time in enumerate(times[:-1]):
			state = states[step]			
			action = controller.policy(state) 
			reward += env.reward()
			states[step + 1], _, done, _ = env.step(action)
			actions[step] = action
			if done:
				break
		print('reward: ',reward)
		env.close()
		return states, actions

	def extract_gains(controller, states):
		kp = zeros((len(times)-1,1))
		kd = zeros((len(times)-1,1))
		i = 0
		for state in states[1:]:
			kp[i] = controller.get_kp(state)
			kd[i] = controller.get_kd(state)
			i += 1
		return kp,kd

	def temp(controller,states):
		actions = zeros((len(times) - 1, env.m))	
		step = 0
		for state in states[:-1]:
			action = controller.policy(state)
			actions[step] = action
			step+=1
		return array(actions)

	# environment
	times = param.times
	if param.get('system') is 'CartPole':
		env = CartPole()

	# get controllers
	deeprl_controller = torch.load(param.get('rl_model_fn'))
	pid_controller = torch.load(param.get('gains_model_fn'))
	plain_pid_controller = PlainPID([2, 40], [4, 20])

	# run sim
	initial_state = env.reset() # [1, pi/4, 0, 0]
	states_deeprl, actions_deeprl = run_sim(deeprl_controller, initial_state)
	# actions_pid = temp(pid_controller,states_deeprl)
	states_pid, actions_pid = run_sim(pid_controller, initial_state)
	stated_plain_pid, actions_plain_pid = run_sim(plain_pid_controller, initial_state)

	# extract gains
	kp,kd = extract_gains(pid_controller,states_pid)

	# plots
	for i in range(env.n):
		fig, ax = plotter.plot(times,states_deeprl[:,i],title=param.get('states_name')[i])
		plotter.plot(times,states_pid[:,i], fig = fig, ax = ax)
		plotter.plot(times,stated_plain_pid[:,i], fig = fig, ax = ax)
	for i in range(env.m):
		fig, ax = plotter.plot(times[1:],actions_deeprl[:,i],title=param.get('actions_name')[i])
		plotter.plot(times[1:],actions_pid[:,i], fig = fig, ax = ax)
		plotter.plot(times[1:],actions_plain_pid[:,i], fig = fig, ax = ax)

	fig,ax = plotter.plot(times[1:],kp,title='Kp')
	fig,ax = plotter.plot(times[1:],kd,title='Kd')


	plotter.save_figs()
	plotter.open_figs()

	# visualize 3D
	if visualize:
		import meshcat
		import meshcat.geometry as g
		import meshcat.transformations as tf
		import time

		# Create a new visualizer
		vis = meshcat.Visualizer()
		vis.open()

		vis["cart"].set_object(g.Box([0.5,0.2,0.2]))
		vis["pole"].set_object(g.Cylinder(param.get('sys_length_pole'), 0.01))
		for t, state in zip(times, states_deeprl):
			vis["cart"].set_transform(tf.translation_matrix([state[0], 0, 0]))

			vis["pole"].set_transform(
				tf.translation_matrix([state[0], 0, param.get('sys_length_pole')/2]).dot(
					tf.euler_matrix(pi/2, state[1], 0)))

			time.sleep(0.01)

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("--animate", action='store_true')
	args = parser.parse_args()
	main(args.animate)