
# my packages
from learning.ppo import PPO
from learning.ddpg import DDPG

# standard packages
import torch 
from torch.distributions import MultivariateNormal,Categorical
from torch.optim.lr_scheduler import ReduceLROnPlateau
import numpy as np 

class ReduceLROnRewardSchedule:
	def __init__(self,optimizer):
		self.optimizer = optimizer
		self.initial_lr = optimizer.param_groups[0]['lr']
		self.gamma = 0.5
		self.reward_schedule = np.append(np.array(-np.Inf),np.arange(-1200,0,200))
		# print('reward schedule: ', self.reward_schedule)

	def step(self,reward):
		k = np.where(reward > self.reward_schedule)[0][-1]
		for param_group in self.optimizer.param_groups:
			lr = self.initial_lr*(self.gamma**k)
			if param_group['lr'] >= lr:
				print("Changing Learning Rate From: %5f to %5f"%((param_group['lr'],lr)))
				param_group['lr'] = lr


def train_rl(param, env):

	continuous = param.rl_continuous_on
	if param.rl_continuous_on:
		print('Continuous Action Space')
	else:
		print('Discrete Action Space: ',param.rl_discrete_action_space)
	print("Case: ", param.env_case)

	state_dim = env.n
	action_dim = env.m
	times = param.sim_times

	# random seed
	random_seed = 1
	if random_seed:
		print("Random Seed: {}".format(random_seed))
		torch.manual_seed(random_seed)
		env.seed(random_seed)
		np.random.seed(random_seed)

	# exit condition
	solved_reward = 0.97*env.max_reward*param.sim_nt
	print('Solved Reward: ',solved_reward)

	# init model 
	if param.rl_warm_start_on:
		print('Loading Previous Model: ', param.rl_warm_start_fn)
		model = torch.load(param.rl_warm_start_fn)
		if continuous:
			model.make_replay_buffer(int(param.rl_buffer_limit))
		print(model)
	else:
		print('Creating New Model...')
		if continuous:
			model = DDPG(
				param.rl_mu_network_architecture,
				param.rl_q_network_architecture,
				param.rl_network_activation,
				param.a_min,
				param.a_max,
				param.rl_action_std,
				param.rl_max_action_perturb,
				param.rl_lr_mu,
				param.rl_lr_q,
				param.rl_tau,
				param.rl_gamma,
				param.rl_batch_size,
				param.rl_K_epoch,
				param.rl_buffer_limit,
				param.rl_gpu_on)
		else:
			model = PPO(
				param.rl_discrete_action_space, 
				state_dim,
				action_dim,
				param.rl_action_std,
				param.rl_gpu_on,
				param.rl_lr, 
				param.rl_gamma, 
				param.rl_K_epoch, 
				param.rl_lmbda, 
				param.rl_eps_clip)

	if param.rl_lr_schedule_on:
		schedulers = []
		for optimizer in model.get_optimizers():
			# schedulers.append(ReduceLROnPlateau(optimizer, mode='max'))
			schedulers.append(ReduceLROnRewardSchedule(optimizer))

	# logging variables
	running_reward = 0
	trial_count = 0
	best_reward = -np.Inf
	data_count = 0

	# training loop
	for i_episode in range(1, param.rl_max_episodes+1):
		while data_count <= param.rl_batch_size:
			s = env.reset()
			done = False
			trial_count += 1.
			for step, time in enumerate(times[:-1]):

				if continuous:
					a = model.train_policy(s)
					s_prime, r, done, _ = env.step(a)
					model.put_data((s,a,r,s_prime,done))

				else:
					prob = model.pi(torch.from_numpy(s).float())
					c = Categorical(prob).sample().item()
					a = model.class_to_force(c)
					s_prime, r, done, _ = env.step([a])
					model.put_data((s,c,r,s_prime,prob[c].item(),done))

				s = s_prime
				running_reward += r
				data_count += 1
				if done:
					break

		model.train_net()
		data_count = 0
		
		# stop training if avg_reward > solved_reward
		if running_reward/trial_count > solved_reward:
			print('Episode {} \t Avg reward: {:2f}'.format(i_episode, running_reward/trial_count))
			print("########## Solved! ##########")
			temp_buffer = model.data
			model.data = []
			torch.save(model, param.rl_train_model_fn)
			model.data = temp_buffer
			break
					
		# logging
		if i_episode % param.rl_log_interval == 0:			
			print('Episode {} \t Avg reward: {:2f}'.format(i_episode, running_reward/trial_count))
			
			# save best iteration
			if running_reward/trial_count > best_reward:
				best_reward = running_reward/trial_count
				print('   saving best model')
				temp_buffer = model.data
				model.data = []
				torch.save(model, param.rl_train_model_fn)
				model.data = temp_buffer

			# update learning rate
			if param.rl_lr_schedule_on:
				for scheduler in schedulers:
					scheduler.step(running_reward/trial_count)

			running_reward = 0
			trial_count = 0 
