#!/usr/bin/env python2

import unittest
import pocketcorr as pc

class TestPOCO(unittest.TestCase):
    def setUp(self):
        self.poco = pc.POCO('localhost')

    def test_ant_ext(self):
        for ant in [4, 8, 16]:
            self.poco.antennas = ant
            antennas = map(self.poco.get_ant_ext, range(self.poco.antennas))
            correct = [chr(ord('a') + i) for i in range(self.poco.antennas)]
            for a, c in zip(antennas, correct):
                self.assertEqual(a, c)

    def test_poco_ant_ind(self):
        for ant in [6, 8, 12, 16, 32]:
            self.poco.antennas = ant
            for i in range(32):
                if ant % 6 == 0:
                    chanu = chr(ord('A')+i/(ant/3)) + str(1+i%(ant/3))
                    chanl = chr(ord('a')+i/(ant/3)) + str(1+i%(ant/3))
                else:
                    chanu = chr(ord('A')+i/(ant/8)) + str(1+i%(ant/8))
                    chanl = chr(ord('a')+i/(ant/8)) + str(1+i%(ant/8))
                if i < ant:
                    self.assertEqual(self.poco.get_ant_ind(chanu), i)
                    self.assertEqual(self.poco.get_ant_ind(chanl), i)
                else:
                    with self.assertRaises(ValueError):
                        self.assertEqual(self.poco.get_ant_ind(chanu), i)
                    with self.assertRaises(ValueError):
                        self.assertEqual(self.poco.get_ant_ind(chanl), i)

    def test_ant_index(self):
        # Only testing rpoco8, rpoco16, and snap
        bof = 'rpoco8'
        for i in range(8):
            self.assertEqual(pc.get_ant_index(bof, i), i)
            self.assertEqual(pc.get_ant_index(bof, str(i)), i)
            self.assertEqual(pc.get_ant_index(bof, chr(ord('a')+i)), i)
            self.assertEqual(pc.get_ant_index(bof, chr(ord('a')+i)+'1'), i)

        for i in range(32):
            chan = chr(ord('a')+i/4) + str(1+i%4)
            if i % 4:
                with self.assertRaises(ValueError):
                    pc.get_ant_index(bof, chan)
            if i >= 8:
                with self.assertRaises(ValueError):
                    pc.get_ant_index(bof, i)
                with self.assertRaises(ValueError):
                    pc.get_ant_index(bof, str(i))
                with self.assertRaises(ValueError):
                    pc.get_ant_index(bof, chr(ord('a')+i))

        bof = 'rpoco16'
        for i in range(16):
            chan = chr(ord('a')+i/2) + str(1+i%2)
            self.assertEqual(pc.get_ant_index(bof, chan), i)

        for i in range(32):
            chan = chr(ord('a')+i/4) + str(1+i%4)
            if i % 4 > 1:
                with self.assertRaises(ValueError):
                    pc.get_ant_index(bof, chan)

        bof = 'spoco12'
        # XXX

    def test_get_model(self):
        model_info = {'rpoco8':(1, 8, 'rpoco8_100.bof'),
                      'rpoco8_r2': (2, 8, 'rpoco8_100_r2.bof'),
                      'rpoco16': (2, 16, 'rpoco16_100.bof')}
        for roach in model_info.keys():
            model = model_info[roach][0]
            antennas = model_info[roach][1]
            boffile = model_info[roach][2]
            self.poco.get_model(roach)
            self.assertEqual(self.poco.model, model)
            self.assertEqual(self.poco.antennas, antennas)
            self.assertEqual(self.poco.boffile, boffile)

    def test_xmult_table(self):
        for ant in [4, 8, 16]:
            with open('xmult' + str(ant) + '.csv') as f:
                corrtable = [l[:-1].split(',') for l in f.readlines()]

            # Convert the xmult table to how the get_xmult function outputs.
            xmult = [filter(len, line) for line in corrtable[:ant]]
            xmult = reduce(lambda x, y: x+y, xmult, [])
            index = lambda i: ord(i) - ord('a')
            xmult = [(index(x[0]), index(x[1])) for x in xmult]

            # Get the xmult table using python
            self.poco.antennas = ant
            fst, snd = self.poco.get_xmult()
            xlist = [(min(*x), max(*x)) for x in fst + snd]
            self.assertEqual(sorted(xmult), sorted(xlist))

            # test the mapping between first and second.
            mapping = corrtable[-2:]
            mapping = [[ord(c) - ord('a') for c in m] for m in mapping]
            mapping = dict(zip(*mapping))
            for p1, p2 in zip(fst, snd):
                self.assertEqual((mapping[p1[0]], mapping[p1[1]]), p2)

    def test_set_attributes(self):
        self.poco.get_model('rpoco8')
        self.poco.set_attributes('psa898_v003', 200e6, 2)
        self.assertEqual(self.poco.sdf, -1 * 0.2 / 2 / self.poco.nchan)
        self.assertEqual(self.poco.sfreq, 0.2)

    def test_scheduler(self):
        # not much to do here but check failure cases
        with self.assertRaises(ValueError):
            self.poco.scheduler(10, None, '2000-01-01-00:00')
        with self.assertRaises(ValueError):
            self.poco.scheduler(10, None, None, 'I,10')
        with self.assertRaises(ValueError):
            self.poco.scheduler(None, None, '2000-01-01-00:00', 'I,10')
        with self.assertRaises(ValueError):
            self.poco.scheduler(10, None, '2000-01-01-00:00', 'I,10')
        with self.assertRaises(ValueError):
            self.poco.scheduler(10, '2000-01-01-00:00')
        with self.assertRaises(ValueError):
            self.poco.scheduler(None, '2000-01-01-00:00', '1999-01-01-00:00')

    def test_mode_conv(self):
        # board, board version, demux, number of antennas
        modelist_all = [(['roach', 1, 1,  8], 16689),
                        (['roach', 2, 1,  8], 16721),
                        (['roach', 2, 1, 16], 33105),
                        (['roach', 2, 2, 16], 33361),
                        (['snap',  1, 1, 12], 24882),
                        (['snap',  1, 2,  6], 12850)]
        for mode in modelist_all:
            modelist_in, modenum_in = mode
            self.assertEqual(pc.mode_list2int(modelist_in), modenum_in)
            modelist_out = pc.mode_int2list(modenum_in)
            for i, o in zip(modelist_in, modelist_out):
                self.assertEqual(i, o)

if __name__ == '__main__':
    unittest.main()
