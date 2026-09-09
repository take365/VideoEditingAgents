# Cool Sheep Pet Transition Frames

In-between frames for simple flipbook-style motion between the main pet action images.

## Recommended folder

Use `pet_ready_1024x1536/` for implementation.

These files are transparent PNGs with a consistent 1024x1536 canvas:

- `01_idle_to_wave.png`
- `02_wave_to_thinking.png`
- `03_thinking_to_working.png`
- `04_working_to_success.png`
- `05_success_to_confused.png`
- `06_confused_to_pointing.png`
- `07_pointing_to_sleeping.png`
- `08_sleeping_to_running.png`
- `09_running_to_idle.png`

## Suggested flipbook order

```text
../pet_ready_1024x1536/01_idle.png
pet_ready_1024x1536/01_idle_to_wave.png
../pet_ready_1024x1536/02_wave.png
pet_ready_1024x1536/02_wave_to_thinking.png
../pet_ready_1024x1536/03_thinking.png
pet_ready_1024x1536/03_thinking_to_working.png
../pet_ready_1024x1536/04_working_laptop.png
pet_ready_1024x1536/04_working_to_success.png
../pet_ready_1024x1536/05_success.png
pet_ready_1024x1536/05_success_to_confused.png
../pet_ready_1024x1536/06_confused_error.png
pet_ready_1024x1536/06_confused_to_pointing.png
../pet_ready_1024x1536/07_pointing.png
pet_ready_1024x1536/07_pointing_to_sleeping.png
../pet_ready_1024x1536/08_sleeping.png
pet_ready_1024x1536/08_sleeping_to_running.png
../pet_ready_1024x1536/09_running.png
pet_ready_1024x1536/09_running_to_idle.png
../pet_ready_1024x1536/01_idle.png
```

## Review files

- `transition_contact_sheet.png`: transition frames only.
- `pet_flipbook_preview.gif`: rough preview of key frames plus transition frames.
