import socket
import json
import os
import fcntl
import errno

# Klipper module for socket communication. Running START_COMMS will enable the printer to start listening. Should be nonblocking

# While moving, the printer will ignore for all commands until the movement is complete

class workcell_controller:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.camera_loop_path = "/tmp/camera_loop.sock"
        self.camera_ctrl_path = "/tmp/camera_ctrl.sock"
        self.camera_loop_srv = None
        self.camera_ctrl_srv = None
        self.reactor = self.printer.get_reactor()
        self.current_command = None
        self.requested_command = False
        self.tag_id = None
        
        self.timer = None
        
        self.printer.register_event_handler('klippy:ready', self._start)
        self.printer.register_event_handler('klippy:shutdown', self._shutdown)
        self.printer.register_event_handler('klippy:disconnect', self._shutdown)
        
        self.gcode.register_command('APRILTAGS', self._cmd_APRILTAGS)
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
        if not self._toolhead_is_busy(eventtime) and self.current_command is None and not self.requested_command:
            self.requested_command = True
            self._send_request_command()
        self._drain_socket(self.camera_loop_srv)
        if self.current_command is not None:
            if not self._toolhead_is_busy(eventtime):
                if self.current_command != "DONE":
                    self.gcode.run_script_from_command(self.current_command)
                    self.current_command = None
                    self.requested_command = False
                    return self.reactor.monotonic() + 0.1
                else:
                    self.reactor.unregister_timer(self.timer)
                    self.timer = None
                    self.gcode.respond_info(f"[Test] Detected tag {self.tag_id}")
                    self.tag_id = None
                    return None
            else:
                return self.reactor.monotonic() + 0.1
        else:
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
            
    def _cmd_APRILTAGS(self, gcmd):
        tag_id = gcmd.get_int('TAG_ID')
        if tag_id is None:
            self.gcode.respond_info("[Test] No tag ID provided")
            return
        self.tag_id = tag_id
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
            
    def _toolhead_is_busy(self, eventtime):
        toolhead = self.printer.lookup_object('toolhead')
        # for part in command.split():
        #     if part.startswith('Z'):
        #         return True
        print_time, est_print_time, lookahead_empty = toolhead.check_busy(eventtime)
        idle_time = est_print_time - print_time
        if lookahead_empty and idle_time > 0.05:
            return False
        else:
            return True
        
    def _send_request_command(self):
        self.camera_ctrl_srv.accept(self.camera_ctrl_path)
        self.camera_ctrl_srv.sendall(f"REQUEST {self.tag_id}".encode())
        
def load_config(config):
    return workcell_controller(config)