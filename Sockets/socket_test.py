import socket
import json
import os
import fcntl
import errno

# Klipper module for socket communication. Running START_COMMS will enable the printer to start listening. Should be nonblocking

class socket_test:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.camera_loop_path = "/tmp/camera_loop.sock"
        self.camera_ctrl_path = "/tmp/camera_ctrl.sock"
        self.camera_loop_srv = None
        self.camera_ctrl_srv = None
        self.reactor = self.printer.get_reactor()
        self.current_command = None
        
        self.timer = None
        
        self.printer.register_event_handler('klippy:ready', self._start)
        self.printer.register_event_handler('klippy:shutdown', self._shutdown)
        self.printer.register_event_handler('klippy:disconnect', self._shutdown)
        
        self.gcode.register_command('START_COMMS', self._cmd_START_COMMS)
        self.gcode.register_command('STOP_COMMS', self._cmd_STOP_COMMS)
        
        
    def _start(self):
        self.camera_loop_srv = self._bind_socket(self.camera_loop_path)
        self.camera_ctrl_srv = self._bind_socket(self.camera_ctrl_path)
        
    def _shutdown(self, *a, **kw):
        if self.timer is not None:
            self.reactor.unregister_timer(self.timer)
            self.timer = None
        if self.camera_loop_srv:
            self.camera_loop_srv.close()
        if self.camera_ctrl_srv:
            self.camera_ctrl_srv.close()
        
    def _bind_socket(self, path):
        if os.path.exists(path):
            os.unlink(path)
        if path == self.camera_loop_path:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        elif path == self.camera_ctrl_path:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(path)
        os.chmod(path, 0o666)
        fcntl.fcntl(s, fcntl.F_SETFL, os.O_NONBLOCK)
        return s
    
    def _tick(self, eventtime):
        self._drain_socket(self.camera_loop_srv)
        if self.current_command is not None:
            self.gcode.run_script_from_command(self.current_command)
            self.current_command = None
            # Reschedule for next check
            return self.reactor.monotonic() + 0.2
        else:
            # No data, check less frequently
            return self.reactor.monotonic() + 1
        
        
    def _drain_socket(self, srv):
        if srv is None:
            return
        try:
            data, addr = srv.recvfrom(1024)
            self.current_command = data.decode()
        except OSError as e:
            if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                pass
            else:
                self.gcode.respond_info(f"[Test] _drain_socket() error: {e}")
        except Exception as e:
            self.gcode.respond_info(f"[Test] _drain_socket() error: {e}")
            
    def _cmd_START_COMMS(self, gcmd):
        if self.timer is not None:
            self.gcode.respond_info("[Test] Socket already running")
            return
        self.timer = self.reactor.register_timer(self._tick, self.reactor.NEVER)
        self.reactor.update_timer(self.timer, self.reactor.monotonic() + 0.02)
        self.gcode.respond_info("[Test] Socket started")
        
    def _cmd_STOP_COMMS(self, gcmd):
        if self.timer is not None:
            self.reactor.unregister_timer(self.timer)
            self.timer = None
            self.gcode.respond_info(f"[Test] Turning off socket")
        else:
            self.gcode.respond_info(f"[Test] Socket was already off")
        self.current_command = None
        
def load_config(config):
    return socket_test(config)