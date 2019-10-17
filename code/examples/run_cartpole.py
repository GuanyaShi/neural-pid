from param import Param
from run import run
from systems.cartpole import CartPole
import numpy as np
import torch

class CartpoleParam(Param):
	def __init__(self):
		super().__init__()
		self.env_name = 'CartPole'
		self.env_case = 'SmallAngle' #'SmallAngle','Swing90','Swing180', 'Any90'

		# flags
		self.pomdp_on = False
		self.single_agent_sim = True
		self.multi_agent_sim = False

		# RL
		self.rl_train_model_fn = '../models/CartPole/rl_current.pt'

		# IL
		self.il_train_model_fn = '../models/CartPole/il_current.pt'
		self.il_imitate_model_fn = '../models/CartPole/rl_current.pt'
		self.kp = [2,40]
		self.kd = [4, 20]

		# Sim
		self.sim_t0 = 0
		self.sim_tf = 5
		self.sim_dt = 0.05
		self.sim_times = np.arange(self.sim_t0,self.sim_tf,self.sim_dt)
		self.sim_nt = len(self.sim_times)

		self.sim_rl_model_fn = '../models/CartPole/rl_current.pt'
		self.sim_il_model_fn = '../models/CartPole/il_current.pt'
		self.sim_render_on = False

		self.controller_class = 'Ref' # PID, PID_wRef, Ref

		# planning
		# self.rrt_fn = '../models/CartPole/rrt.csv'
		self.scp_fn = '../models/CartPole/scp.csv'
		self.scp_pdf_fn = '../models/CartPole/scp.pdf'

class PlainPID:
	"""
	Simple PID controller with fixed gains
	"""
	def __init__(self, Kp, Kd):
		self.Kp = Kp
		self.Kd = Kd

	def policy(self, state):
		action = (self.Kp[0]*state[0] + self.Kp[1]*state[1] + \
			self.Kd[0]*state[2] + self.Kd[1]*state[3])
		return action


if __name__ == '__main__':
	param = CartpoleParam()
	env = CartPole(param)

	controllers = {
		'RL':	torch.load(param.sim_il_model_fn),
		'IL':	torch.load(param.sim_il_model_fn),
		'PID': PlainPID(param.kp, param.kd)
	}
	run(param, env, controllers)
