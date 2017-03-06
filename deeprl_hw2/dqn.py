import tensorflow as tf
import numpy as np

"""Main DQN agent."""

class DQNAgent:
    """Class implementing DQN.

    This is a basic outline of the functions/parameters you will need
    in order to implement the DQNAgnet. This is just to get you
    started. You may need to tweak the parameters, add new ones, etc.

    Feel free to change the functions and funciton parameters that the
    class provides.

    We have provided docstrings to go along with our suggested API.

    Parameters
    ----------
    q_network: keras.models.Model
      Your Q-network model.
    preprocessor: deeprl_hw2.core.Preprocessor
      The preprocessor class. See the associated classes for more
      details.
    memory: deeprl_hw2.core.Memory
      Your replay memory.
    gamma: float
      Discount factor.
    target_update_freq: float
      Frequency to update the target network. You can either provide a
      number representing a soft target update (see utils.py) or a
      hard target update (see utils.py and Atari paper.)
    num_burn_in: int
      Before you begin updating the Q-network your replay memory has
      to be filled up with some number of samples. This number says
      how many.
    train_freq: int
      How often you actually update your Q-Network. Sometimes
      stability is improved if you collect a couple samples for your
      replay memory, for every Q-network update that you run.
    batch_size: int
      How many samples in each minibatch.
    """
    def __init__(self,
                 q_network,
                 preprocessor,
                 memory,
                 policy,
                 gamma,
                 target_update_freq,
                 num_burn_in,
                 train_freq,
                 batch_size,
                 sess):

        self.q_network = q_network
        self.q_values = q_network.output
        self.state = q_network.input
        self.preprocessor = preprocessor
        self.memory = memory
        self.gamma = gamma
        self.policy = policy
        self.target_update_freq = target_update_freq
        self.train_freq = train_freq
        self.num_burn_in = num_burn_in
        self.batch_size = batch_size
        self.sess = sess

    def compile(self, optimizer, loss_func):
        """Setup all of the TF graph variables/ops.

        This is inspired by the compile method on the
        keras.models.Model class.

        This is a good place to create the target network, setup your
        loss function and any placeholders you might need.
        
        You should use the mean_huber_loss function as your
        loss_function. You can also experiment with MSE and other
        losses.

        The optimizer can be whatever class you want. We used the
        keras.optimizers.Optimizer class. Specifically the Adam
        optimizer.
        """

        # Placeholder that we want to feed the value in, just one value
        self.y_true = tf.placeholder(tf.float32, [self.batch_size,])
        # Placeholder that specify which action
        self.action = tf.placeholder(tf.int8, [self.batch_size,])
        # the output of the q_network is y_pred
        y_pred = tf.stack([self.q_values[i, self.action[i]] for i in xrange(self.batch_size)])

        self.loss = loss_func(y_true, y_pred)

        self.optimizer = optimizer.minimize(self.loss)

    def calc_q_values(self, state):
        """Given a state (or batch of states) calculate the Q-values.

        Basically run your network on these states.

        Return
        ------
        Q-values for the state(s)
        """
        q_values_val = self.sess.run(self.q_values, feed_dict={self.state:state})

        return q_values_val

    def select_action(self, state, **kwargs):
        """Select the action based on the current state.

        You will probably want to vary your behavior here based on
        which stage of training your in. For example, if you're still
        collecting random samples you might want to use a
        UniformRandomPolicy.

        If you're testing, you might want to use a GreedyEpsilonPolicy
        with a low epsilon.

        If you're training, you might want to use the
        LinearDecayGreedyEpsilonPolicy.

        This would also be a good place to call
        process_state_for_network in your preprocessor.

        Returns
        --------
        selected action
        """

        q_values_val = self.calc_q_values(state)

        return policy.select_action(q_values_val)

    def update_policy(self):
        """Update your policy.

        Behavior may differ based on what stage of training your
        in. If you're in training mode then you should check if you
        should update your network parameters based on the current
        step and the value you set for train_freq.

        Inside, you'll want to sample a minibatch, calculate the
        target values, update your network, and then update your
        target values.

        You might want to return the loss and other metrics as an
        output. They can help you monitor how training is going.
        """

        samples = self.memory.sample(self.batch_size)
        # stack to the first dimension as batch size, which is gooood
        states = np.stack([sample.state for sample in samples])
        actions = np.stack([sample.action for sample in samples])
        y_vals = map(self._calc_y, samples)

        _, loss_val = self.sess.run([self.optimizer, self.loss], feed_dict={self.state:states, \
                                    self.y_true:y_vals, self.action:actions})

        return loss_val

    def fit(self, env, num_iterations, max_episode_length=None):
        """Fit your model to the provided environment.

        Its a good idea to print out things like loss, average reward,
        Q-values, etc to see if your agent is actually improving.

        You should probably also periodically save your network
        weights and any other useful info.

        This is where you should sample actions from your network,
        collect experience samples and add them to your replay memory,
        and update your network parameters.

        Parameters
        ----------
        env: gym.Env
          This is your Atari environment. You should wrap the
          environment using the wrap_atari_env function in the
          utils.py
        num_iterations: int
          How many samples/updates to perform.
        max_episode_length: int
          How long a single episode should last before the agent
          resets. Can help exploration.
        """

        # Get the initial state
        curr_state = np.stack(map(self.preprocessor.process_state_for_network, \
                              [env.step(0)[0] for i in xrange(4)]), axis=2)

        for i in xrange(num_iterations):
            next_state = self._append_to_memory(curr_state)
            self.update_policy()

            print "Loss val : " + str(loss_val)

            curr_state = next_state

    def _calc_y(self, sample):
        y_val = sample.reward
        if not sample.is_terminal:
            y_val += self.gamma * np.max(self.sess.run(self.q_values, feed_dict={self.state:sample.next_state}))

        return y_val

    def _append_to_memory(self, curr_state):
        action = self.select_action(curr_state)
        # Execute action a_t in emulator and observe reward r_t and image x_{t+1}
        next_state, reward, is_terminal, _ = env.step(action)
        # Set s_{t+1} = s_t, a_t, x_{t+1} and preprocess phi_{t+1} = phi(s_{t+1})
        next_state = self.preprocessor.process_state_for_network(next_state)
        next_state = np.expand_dims(next_state, axis = 2)
        # append the next state to the last 3 frames in currstate to form the new state
        next_state = np.append(curr_state[:,:,1:], next_state, axis = 2)

        self.memory.append(curr_state, action, reward, next_state, is_terminal)

        return next_state

    def evaluate(self, env, num_episodes, max_episode_length=None):
        """Test your agent with a provided environment.
        
        You shouldn't update your network parameters here. Also if you
        have any layers that vary in behavior between train/test time
        (such as dropout or batch norm), you should set them to test.

        Basically run your policy on the environment and collect stats
        like cumulative reward, average episode length, etc.

        You can also call the render function here if you want to
        visually inspect your policy.
        """

        while 1:
          env = gym.make('SpaceInvaders-v0')

          curr_state = np.stack([env.step(0)[0] for i in xrange(4)], axis=2)
          curr_state = preprocessor.process_state_for_network(curr_state)
          
          while not is_terminal:
              env.render()
              action = np.argmax(self.sess.run(self.q_values, feed_dict = {self.state:curr_state}))
              next_state, reward, is_terminal, _ = env.step(action)

              next_state = preprocessor.process_state_for_network(next_state)
              next_state = np.expand_dims(next_state, axis = 2)
              # append the next state to the last 3 frames in currstate to form the new state
              next_state = np.append(curr_state[:,:,1:], next_state, axis = 2)

              curr_state = next_state

