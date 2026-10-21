import unittest
try:
    from guitar_player.playback import Player, InputFailure
    from guitar_player.contracts import Action, Note, Plan
    from guitar_player.win_input import input_size, WindowIdentity
except ImportError:
    Player = None


class Clock:
    def __init__(self): self.now = 0.
    def __call__(self): return self.now


class Sender:
    def __init__(self):
        self.sent = []
        self.fail_at = None
    def send(self, action):
        if len(self.sent) == self.fail_at:
            self.fail_at = None
            raise OSError('denied')
        self.sent.append((action.kind, action.value))


class PlaybackTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(Player, 'foreground scheduler is missing')
        self.clock, self.sender = Clock(), Sender()
        self.focus = True
        self.player = Player(self.sender, lambda: self.focus, clock=self.clock, late_budget=.1)
        self.plan = Plan(3., 'keyboard', (Action(0., 'down', 'A'), Action(1., 'up', 'A'), Action(2., 'down', 'Q'), Action(3., 'up', 'Q')), (Note(0., 1., 52, 80), Note(2., 3., 64, 80)), {})

    def test_absolute_deadlines_do_not_accumulate_tick_drift(self):
        self.player.start(self.plan, countdown=0.)
        for t in (0., 1.01, 2.01, 3.01):
            self.clock.now = t
            self.player.tick()
        self.assertEqual(self.sender.sent, [('down', 'A'), ('up', 'A'), ('down', 'Q'), ('up', 'Q')])
        self.assertEqual(self.player.state, 'STOPPED')

    def test_focus_loss_releases_only_owned_keys_and_never_auto_resumes(self):
        self.player.start(self.plan, countdown=0.)
        self.player.tick()
        self.focus = False
        self.player.tick()
        self.focus = True
        self.clock.now = 2.
        self.player.tick()
        self.assertEqual(self.player.state, 'PAUSED')
        self.assertEqual(self.sender.sent, [('down', 'A'), ('up', 'A')])
        self.assertFalse(self.player.held)

    def test_pause_and_resume_rebuilds_only_current_keyboard_notes(self):
        self.player.start(self.plan, countdown=0.)
        self.player.tick()
        self.clock.now = .4
        self.player.pause()
        self.clock.now = 10.
        self.player.resume(countdown=0.)
        self.player.tick()
        self.clock.now = 10.61
        self.player.tick()
        self.assertEqual(self.sender.sent, [('down', 'A'), ('up', 'A'), ('down', 'A'), ('up', 'A')])

    def test_late_events_stop_without_burst_catchup(self):
        self.player.start(self.plan, countdown=0.)
        self.clock.now = 2.
        self.player.tick()
        self.assertEqual(self.player.state, 'ERROR')
        self.assertEqual(self.sender.sent, [])

    def test_send_failure_releases_previous_success_never_replays_batch(self):
        p = Plan(1., 'keyboard', (Action(0., 'down', 'A'), Action(0., 'down', 'Q'), Action(1., 'up', 'A'), Action(1., 'up', 'Q')), (), {})
        self.sender.fail_at = 1
        self.player.start(p, countdown=0.)
        self.player.tick()
        self.assertEqual(self.sender.sent, [('down', 'A'), ('up', 'A')])
        self.assertEqual(self.player.state, 'ERROR')
        self.assertFalse(self.player.held)

    def test_stop_countdown_is_idempotent_and_blocks_future_notes(self):
        self.player.start(self.plan, countdown=3.)
        self.player.stop()
        self.player.stop()
        self.clock.now = 4.
        self.player.tick()
        self.assertEqual(self.sender.sent, [])

    def test_duplicate_start_rejected(self):
        self.player.start(self.plan)
        with self.assertRaises(RuntimeError): self.player.start(self.plan)

    def test_focus_is_checked_again_between_same_time_actions(self):
        p = Plan(1., 'keyboard', (Action(0., 'down', 'A'), Action(0., 'down', 'Q'), Action(1., 'up', 'A'), Action(1., 'up', 'Q')), (), {})
        self.player.guard = lambda: not self.sender.sent
        self.player.start(p, countdown=0.)
        self.player.tick()
        self.assertEqual(self.sender.sent, [('down', 'A'), ('up', 'A')])

    def test_mouse_owned_button_is_released_on_stop(self):
        p = Plan(1., 'guitar', (Action(0., 'mouse_down', 'left'), Action(1., 'mouse_up', 'left')), (), {})
        self.player.start(p, countdown=0., page_verified=True)
        self.player.tick()
        self.player.stop()
        self.assertEqual(self.sender.sent, [('mouse_down', 'left'), ('mouse_up', 'left')])

    def test_guitar_unknown_page_rejects_start_and_resume(self):
        p = Plan(1., 'guitar', (Action(0., 'down', 'T'), Action(1., 'up', 'T')), (), {})
        with self.assertRaises(ValueError): self.player.start(p)
        self.player.start(p, countdown=0., page_verified=True)
        self.player.pause()
        with self.assertRaises(ValueError): self.player.resume(countdown=0.)

    def test_slow_sender_cannot_burst_overdue_following_notes(self):
        original = self.sender.send
        def slow(action):
            original(action)
            if action.kind == 'down': self.clock.now += .3
        self.sender.send = slow
        plan = Plan(1.,'keyboard',(Action(0.,'down','A'),Action(.01,'down','Q'),Action(1.,'up','A'),Action(1.,'up','Q')),(),{})
        self.player.start(plan,countdown=0.)
        self.player.tick()
        self.assertEqual(self.player.state,'ERROR')
        self.assertNotIn(('down','Q'),self.sender.sent)
        self.assertIn(('up','A'),self.sender.sent)

    def test_failed_release_remains_owned_for_stop_retry(self):
        self.player.start(self.plan,countdown=0.)
        self.player.tick()
        self.sender.fail_at = 1
        self.player.stop()
        self.assertIn(('down','A'),self.player.held)
        self.player.stop()
        self.assertFalse(self.player.held)
        self.assertEqual(self.sender.sent[-1],('up','A'))

    def test_win32_input_abi_size(self):
        import ctypes
        self.assertEqual(input_size(), 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)


if __name__ == '__main__': unittest.main()
