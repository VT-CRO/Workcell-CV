import socket
import json
import os
import fcntl
import errno

class workcell_controller:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.command_socket_path = "/tmp/command_socket.sock"
        self.control_socket_path = "/tmp/control_socket.sock"
        self.command_socket = None
        self.control_socket = None
        self.reactor = self.printer.get_reactor()
        self.timer = None
        
        # self.printer.register_event_handler('klippy:ready', self._start)
        self.printer.register_event_handler('klippy:shutdown', self._shutdown)
        self.printer.register_event_handler('klippy:disconnect', self._shutdown)
        
        self.gcode.register_command('APRILTAGS', self._cmd_APRILTAGS)
        # self.gcode.register_command('STOP_COMMS', self._cmd_STOP_COMMS)
        
    # def _start(self):
    #     self.camera_loop_srv = self._bind_socket(self.camera_loop_path)
    #     self.camera_ctrl_srv = self._bind_socket(self.camera_ctrl_path)
        
    def _shutdown(self, *a, **kw):
        if self.timer is not None:
            self.reactor.unregister_timer(self.timer)
            self.timer = None
        if self.command_socket:
            self.command_socket.close()
        if self.control_socket:
            self.control_socket.close()
            
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
            
    def _cmd_APRILTAGS(self, gcmd):
        tag_id = gcmd.get_int('TAG_ID')
        if tag_id is None:
            self.gcode.respond_info("[Workcell Controller] No tag ID provided")
            return
        self.tag_id = tag_id
        if self.timer is not None:
            self.gcode.respond_info("[Workcell Controller] Socket already running")
            return
        self.command_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        if os.path.exists(self.command_socket_path):
            os.unlink(self.command_socket_path)
        self.command_socket.bind(self.command_socket_path)
        self.control_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.control_socket.connect(self.control_socket_path)
            self.control_socket.send(f"START {tag_id}".encode())
            self.control_socket.close()
        except Exception as e:
            self.gcode.respond_info(f"[Workcell Controller] Error connecting to control socket, is auto calibrator running?")
        self.timer = self.reactor.register_timer(self._tick, self.reactor.NEVER)
        self.reactor.update_timer(self.timer, self.reactor.monotonic() + 0.1)
        self.gcode.respond_info(f"[Workcell Controller] Moving to tag {tag_id}")
        
    def _drain_socket(self):
        try:
            data, addr = self.command_socket.recvfrom(1024)
            command = data.decode()
            return command
        except OSError as e:
            if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                pass
            else:
                self.gcode.respond_info(f"[Test] _drain_socket() error: {e}")
        except Exception as e:
            self.gcode.respond_info(f"[Test] _drain_socket() error: {e}")
            
        return None
        
    def _tick(self, eventtime):
        if not self._toolhead_is_busy(eventtime):
            self.control_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.control_socket.connect(self.control_socket_path)
            self.control_socket.send(f"REQUEST {self.tag_id}".encode())
            self.control_socket.close()
            command = self._drain_socket()
            if command is not None:
                if command == "DONE":
                    self.gcode.respond_info(f"[Workcell Controller] Detected tag {self.tag_id}")
                    self.tag_id = None
                    if self.control_socket:
                        self.control_socket.close()
                    self.reactor.unregister_timer(self.timer)
                    self.timer = None
                    return self.reactor.NEVER
                if self._toolhead_is_busy(eventtime):
                    return self.reactor.monotonic() + 0.1
                else:
                    self.gcode.run_script_from_command(command)
                    return self.reactor.monotonic() + 0.1
        else:
            return self.reactor.monotonic() + 0.1
                
            
def load_config(config):
    return workcell_controller(config)      
# command = self._drain_socket()
#         if command is not None:
#             if not self._toolhead_is_busy(eventtime):
#                 return self.reactor.monotonic() + 0.1
#             else:
#                 self.gcode.respond_info(f"[Workcell Controller] Toolhead is not busy, sending command")
#                 self.gcode.respond_info(f"[Workcell Controller] Moving to tag {self.tag_id}")
#                 return self.reactor.monotonic() + 0.1