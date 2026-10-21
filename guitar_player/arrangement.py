from collections import defaultdict
from .contracts import Action, Note, Plan
from .profiles import KEYBOARD_KEYS, KEYBOARD_VERSION
from .storage import content_hash


def keyboard_plan(source, max_polyphony=None):
    if not source.notes:
        raise ValueError('未识别出可演奏音符，请换一首歌')
    low, high = min(n.pitch for n in source.notes), max(n.pitch for n in source.notes)
    offsets = [o for o in range(-120, 121, 12) if 52 <= low+o and high+o <= 87]
    offset = min(offsets, key=abs) if offsets else 0
    by_key = defaultdict(list)
    changes, retriggered = [], []
    for n in source.notes:
        pitch = n.pitch + offset
        while pitch < 52:
            pitch += 12
        while pitch > 87:
            pitch -= 12
        if pitch != n.pitch:
            changes.append({'time': n.start, 'from': n.pitch, 'to': pitch})
        by_key[pitch].append(Note(n.start, n.end, pitch, n.velocity))
    notes = []
    for pitch, group in by_key.items():
        group.sort(key=lambda n: (n.start, -n.velocity, -n.end))
        for i, n in enumerate(group):
            next_start = group[i+1].start if i+1 < len(group) else source.duration
            end = min(n.end, next_start)
            if end < n.end:
                retriggered.append({'time': n.start, 'end': n.end, 'adapted_end': end, 'pitch': pitch})
            if end > n.start:
                notes.append(Note(n.start, end, pitch, n.velocity))
    notes.sort(key=lambda n: (n.start, n.pitch))
    actions = []
    for n in notes:
        key = KEYBOARD_KEYS[n.pitch-52]
        actions.extend((Action(n.start, 'down', key), Action(n.end, 'up', key)))
    actions.sort(key=lambda a: (a.time, a.kind != 'up', str(a.value)))
    count = peak = 0
    for a in actions:
        count += 1 if a.kind == 'down' else -1
        peak = max(peak, count)
    if max_polyphony is not None and peak > max_polyphony:
        raise ValueError('复音超出已校准限制，不能静默丢弃声部')
    report = {'source_hash': content_hash(source.to_dict()), 'profile': KEYBOARD_VERSION, 'pitch_changes': changes, 'retriggered': retriggered, 'peak_polyphony': peak, 'pedal_not_supported_in_game': bool(source.controls), 'timing_verified_in_game': False}
    return Plan(source.duration, 'keyboard', tuple(actions), tuple(notes), report)


def guitar_plan(source, profile):
    """Build a conservative chord-strum plan from a verified local profile.

    The profile is deliberately required at runtime: an unverified chord table
    would turn a plausible-looking plan into blind clicks in the game.
    """
    if profile is None:
        raise ValueError('吉他模式需要先完成图形校准')
    if not hasattr(profile, 'validate_ready'):
        raise ValueError('吉他配置无效，请重新校准')
    profile.validate_ready()
    if not source.notes:
        raise ValueError('未识别出可演奏音符，请换一首歌')
    chords = tuple(profile.chords)
    actions, rendered_notes = [], []
    approximated = []
    last_page, previous_end = 0, -1.
    lead = 3 * profile.page_seconds + profile.select_seconds
    groups = defaultdict(list)
    for note in source.notes:
        groups[round(note.start, 6)].append(note)
    for start, notes_at_time in sorted(groups.items()):
        pitch_classes = {note.pitch % 12 for note in notes_at_time}
        chord = max(chords, key=lambda item: (len(pitch_classes & {p % 12 for p in item.pitches}), -item.page, -item.slot))
        attack = start + lead
        steps = (chord.page - last_page) % 4
        setup = attack - profile.select_seconds - steps * profile.page_seconds
        if setup < previous_end:
            raise ValueError(f'{start:.2f}秒附近起音过密，分页/扫弦准备来不及；请换键盘模式')
        for step in range(steps):
            when = setup + step * profile.page_seconds
            actions.extend((Action(when, 'down', profile.next_key),
                            Action(when + min(.02, profile.page_seconds/4), 'up', profile.next_key),
                            Action(when + profile.page_seconds, 'verify_page', (last_page + step + 1) % 4)))
        last_page = chord.page
        end = attack + profile.strum_seconds
        actions.extend((Action(attack-profile.select_seconds, 'move', chord.slot),
                        Action(attack, 'move', 6), Action(attack, 'mouse_down', 'left'),
                        Action(end, 'move', 7), Action(end, 'mouse_up', 'left')))
        previous_end = end
        note_end = max(end, max(n.end for n in notes_at_time) + lead)
        rendered_notes.extend(Note(attack, note_end, pitch, max(n.velocity for n in notes_at_time)) for pitch in chord.pitches)
        approximated.append({'time': start, 'chord': chord.name, 'page': chord.page, 'slot': chord.slot, 'source_notes': len(notes_at_time)})
    actions.sort(key=lambda action: action.time)
    actions.insert(0, Action(0., 'verify_page', 0))
    report = {
        'source_hash': content_hash(source.to_dict()),
        'profile': 'guitar-four-page-v1',
        'chords': approximated,
        'approximated': True,
        'pre_roll_seconds': lead,
        'mouse_gesture_verified': profile.verified,
        'timing_verified_in_game': False,
        'pedal_not_supported_in_game': bool(source.controls),
    }
    duration = max(source.duration + lead, max(a.time for a in actions), max(n.end for n in rendered_notes))
    # The same chord may be restruck before its reference tail ends.
    by_pitch = defaultdict(list)
    for note in rendered_notes:
        by_pitch[note.pitch].append(note)
    reference = []
    for group in by_pitch.values():
        group.sort(key=lambda n: n.start)
        for index, note in enumerate(group):
            end = min(note.end, group[index+1].start) if index+1 < len(group) else note.end
            if end > note.start:
                reference.append(Note(note.start, end, note.pitch, note.velocity))
    return Plan(duration, 'guitar', tuple(actions), tuple(sorted(reference, key=lambda n: (n.start,n.pitch))), report)
