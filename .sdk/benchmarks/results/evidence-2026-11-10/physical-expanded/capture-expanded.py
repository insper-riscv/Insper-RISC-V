import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path('/review/SDK')
def command(args):
    p=subprocess.run(args,cwd=root,text=True,capture_output=True,timeout=30)
    if p.returncode: raise RuntimeError(p.stderr)
    return p.stdout.strip()
sof=root/'src/simulation/internal-mem/quartus/output_files/core_fpga_test.sof'
report=dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sdk_commit=command(['git','rev-parse','HEAD']),
    submodules=command(['git','submodule','status','--recursive']),
    core_dirty=command(['git','-C','Core','status','--porcelain']),
    jtag_inventory=command(['jtagconfig']),
    selected_cable='USB-Blaster [1-2]',selected_idcode='02B050DD',
    bitstream_path=str(sof),bitstream_sha256=hashlib.sha256(sof.read_bytes()).hexdigest(),
    clock_hz_nominal=50_000_000, clock_measurement='PLL configuration; no external frequency measurement',
    unchanged_hardware_report_reference='physical-previous/quartus',
    note='Only the authorized Cyclone V cable was programmed; no global jtagd reset.')
assert report['bitstream_sha256']=='a007bc325b1d99410a2454f50b41f2cb166c0e68d3a897548a84e6d1151c8aed'
assert not report['core_dirty']
Path('/review/expanded-context.json').write_text(json.dumps(report,indent=2)+'\n')
print('Physical context captured; matched bitstream and clean Core confirmed')
