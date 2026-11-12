# GPIO C driver example

Register the matching SDK and open this folder in VS Code. Run Prepare Project, then Simulate. The default modular map provides SWITCHES at 0x90000000 and KEYS at 0xA0000000. The generator resolves these from the YAML; they are not embedded in the application.

Expected output is `GPIO set/clear/toggle, pins, IRQ read-clear and two instances: PASS`. Inspect `vendor/GPIO` after preparation. This SDK example is simulation-only; Program FPGA refuses the modular platform. The default internal-mem and DE0-CV SDK maps do not expose GPIO.
