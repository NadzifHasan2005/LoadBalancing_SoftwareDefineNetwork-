# Software Define Network
## 1. Simple Topology
<img width="470" height="210" alt="image" src="https://github.com/user-attachments/assets/c637113c-8a02-40dd-91a4-d6d99ec837e9" />

- Mininet Script
  ```
  from mininet.net import Mininet
  from mininet.node import RemoteController, OVSSwitch
  from mininet.cli import CLI
  from mininet.log import setLogLevel
  
  def simpleTopo():
      net = Mininet(
          controller=RemoteController,
          switch=OVSSwitch,
          autoSetMacs=True
      )
  
      net.addController('c0', ip='127.0.0.1', port=6653)
  
      h1 = net.addHost('h1', ip='10.0.0.1/24')
      h2 = net.addHost('h2', ip='10.0.0.2/24')
      h3 = net.addHost('h3', ip='10.0.0.3/24')
      h4 = net.addHost('h4', ip='10.0.0.4/24')
      
      s1 = net.addSwitch('s1', protocols='OpenFlow13')
      s2 = net.addSwitch('s2', protocols='OpenFlow13')
  
      net.addLink(h1, s1)
      net.addLink(h2, s1)
      net.addLink(s1, s2)
      net.addLink(h3, s2)
      net.addLink(h4, s2)
  
      net.start()
      CLI(net)
      net.stop()
  
  if __name__ == '__main__':
      setLogLevel('info')
      simpleTopo()

  ```
  Jalankan dengan command
  ```
  sudo python3 (nama file.py)
  ```
- Ryu Script
  Use command
  ```
  ryu-manager ryu.app.simple_switch_13
  ```
---

## 2. Complex Topology
<img width="485" height="383" alt="image" src="https://github.com/user-attachments/assets/619c2802-e278-4d33-9999-4ecc33f8831b" />

- Mininet
  ```
  from mininet.topo import Topo
  from mininet.net import Mininet
  from mininet.node import RemoteController, OVSSwitch
  from mininet.cli import CLI
  from mininet.log import setLogLevel
  
  class ComplexTopo(Topo):
      def build(self):
          s1 = self.addSwitch('s1', protocols='OpenFlow13')
          s2 = self.addSwitch('s2', protocols='OpenFlow13')
          s3 = self.addSwitch('s3', protocols='OpenFlow13')
  
          h1 = self.addHost('h1', ip='10.0.0.1/24')
          h2 = self.addHost('h2', ip='10.0.0.2/24')
          h3 = self.addHost('h3', ip='10.0.0.3/24')
          h4 = self.addHost('h4', ip='10.0.0.4/24')
          h5 = self.addHost('h5', ip='10.0.0.5/24')
          h6 = self.addHost('h6', ip='10.0.0.6/24')
  
  
          self.addLink(s1, h1, 1)
          self.addLink(s1, h2, 2)
          self.addLink(s2, h3, 1)
          self.addLink(s2, h4, 2)
          self.addLink(s3, h5, 1)
          self.addLink(s3, h6, 2)
  
          self.addLink(s1, s2, 4, 4)
          self.addLink(s1, s3, 3, 4)
          self.addLink(s2, s3, 3, 3)
  
  
  def run():
      topo = ComplexTopo()
      controller = RemoteController('c0', ip='127.0.0.1', port=6633)
  
      net = Mininet(
          topo=topo,
          controller=controller,
          switch=OVSSwitch,
          autoSetMacs=True
      )
  
      net.start()   # 🔴 WAJIB dulu
  
      # 🔵 AKTIFKAN STP SETELAH NET START
      for s in net.switches:
          s.cmd('ovs-vsctl set bridge {} stp_enable=true'.format(s.name))
  
      CLI(net)
      net.stop()
  
  if __name__ == '__main__': 
  	setLogLevel('info') 
  	run()
  ```
  Jalankan dengan command
  ```
  sudo python3 (nama file.py)
  ```
- Ryu
  ```
  from ryu.base import app_manager
  from ryu.controller import ofp_event
  from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
  from ryu.controller.handler import set_ev_cls
  from ryu.ofproto import ofproto_v1_3
  from ryu.lib.packet import packet
  from ryu.lib.packet import ethernet
  
  
  class ComplexL2Switch(app_manager.RyuApp):
      OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
  
      def __init__(self, *args, **kwargs):
          super(ComplexL2Switch, self).__init__(*args, **kwargs)
          self.mac_to_port = {}   # MAC learning table
  
      # ===== Switch connect =====
      @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
      def switch_features_handler(self, ev):
          datapath = ev.msg.datapath
          ofproto = datapath.ofproto
          parser = datapath.ofproto_parser
  
          # Table-miss flow (send to controller)
          match = parser.OFPMatch()
          actions = [
              parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                     ofproto.OFPCML_NO_BUFFER)
          ]
          self.add_flow(datapath, 0, match, actions)
  
          self.logger.info("Switch %s connected", datapath.id)
  
      def add_flow(self, datapath, priority, match, actions):
          ofproto = datapath.ofproto
          parser = datapath.ofproto_parser
  
          inst = [
              parser.OFPInstructionActions(
                  ofproto.OFPIT_APPLY_ACTIONS, actions)
          ]
  
          mod = parser.OFPFlowMod(
              datapath=datapath,
              priority=priority,
              match=match,
              instructions=inst
          )
          datapath.send_msg(mod)
  
      # ===== Packet In =====
      @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
      def packet_in_handler(self, ev):
          msg = ev.msg
          datapath = msg.datapath
          ofproto = datapath.ofproto
          parser = datapath.ofproto_parser
  
          dpid = datapath.id
          self.mac_to_port.setdefault(dpid, {})
  
          in_port = msg.match['in_port']
  
          pkt = packet.Packet(msg.data)
          eth = pkt.get_protocol(ethernet.ethernet)
  
          # Abaikan LLDP
          if eth.ethertype == 0x88cc:
              return
  
          dst = eth.dst
          src = eth.src
  
          # MAC learning
          self.mac_to_port[dpid][src] = in_port
  
          self.logger.info(
              "DPID=%s SRC=%s DST=%s IN_PORT=%s",
              dpid, src, dst, in_port
          )
  
          # Tentukan output port
          if dst in self.mac_to_port[dpid]:
              out_port = self.mac_to_port[dpid][dst]
          else:
              # Flood tapi aman karena STP aktif di OVS
              out_port = ofproto.OFPP_FLOOD
  
          actions = [parser.OFPActionOutput(out_port)]
  
          # Install flow jika bukan flood
          if out_port != ofproto.OFPP_FLOOD:
              match = parser.OFPMatch(
                  in_port=in_port,
                  eth_src=src,
                  eth_dst=dst
              )
              self.add_flow(datapath, 10, match, actions)
  
          # Packet out
          out = parser.OFPPacketOut(
              datapath=datapath,
              buffer_id=msg.buffer_id,
              in_port=in_port,
              actions=actions,
              data=msg.data
          )
          datapath.send_msg(out)
    ```
    Use command
    ```
    ryu-manager (nama file.py)
    ```
---
## 3. Load balnacing
<img width="432" height="420" alt="image" src="https://github.com/user-attachments/assets/4ec78c20-b645-4d78-bf2a-08e5811a6d68" />

- Mininet
  ```
  from mininet.topo import Topo
  from mininet.net import Mininet
  from mininet.node import RemoteController, OVSSwitch
  from mininet.cli import CLI
  from mininet.log import setLogLevel
  
  class ComplexTopo(Topo):
      def build(self):
          s1 = self.addSwitch('s1', protocols='OpenFlow13')
          s2 = self.addSwitch('s2', protocols='OpenFlow13')
          s3 = self.addSwitch('s3', protocols='OpenFlow13')
          s4 = self.addSwitch('s4', protocols='OpenFlow13')
  
          h1 = self.addHost('h1', ip='10.0.0.1/24')
          h2 = self.addHost('h2', ip='10.0.0.2/24')
  
  
  
          self.addLink(s1, h1, 3)
          self.addLink(s3, h2, 3)
  
          self.addLink(s1, s2, 1, 1)
          self.addLink(s1, s3, 2, 1)
          self.addLink(s2, s4, 2, 1)
          self.addLink(s3, s4, 2, 2)
  
  
  
  def run():
      topo = ComplexTopo()
      controller = RemoteController('c0', ip='127.0.0.1', port=6633)
  
      net = Mininet(
          topo=topo,
          controller=controller,
          switch=OVSSwitch,
          autoSetMacs=True
      )
  
      net.start()
  
      # ❌ STP DIHAPUS (wajib untuk load balancing)
  
      CLI(net)
      net.stop()
  
  if __name__ == '__main__': 
  	setLogLevel('info') 
  	run()
  ```
- Ryu
  ```
  from ryu.base import app_manager
  from ryu.controller import ofp_event
  from ryu.controller.handler import CONFIG_DISPATCHER
  from ryu.controller.handler import set_ev_cls
  from ryu.ofproto import ofproto_v1_3
  
  
  class RyuLoadBalancer(app_manager.RyuApp):
      OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
  
      @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
      def switch_features_handler(self, ev):
          datapath = ev.msg.datapath
          dpid = datapath.id
          ofp = datapath.ofproto
          parser = datapath.ofproto_parser
  
          # ===============================
          # TABLE MISS
          # ===============================
          match = parser.OFPMatch()
          actions = [parser.OFPActionOutput(
              ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
          self.add_flow(datapath, 0, match, actions)
  
          # ===============================
          # ARP FLOOD (WAJIB)
          # ===============================
          match = parser.OFPMatch(eth_type=0x0806)
          actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
          self.add_flow(datapath, 5, match, actions)
  
          # ===============================
          # IPV4 NORMAL FORWARD (BACKUP)
          # ===============================
          match = parser.OFPMatch(eth_type=0x0800)
          actions = [parser.OFPActionOutput(ofp.OFPP_NORMAL)]
          self.add_flow(datapath, 1, match, actions)
  
          # ===============================
          # LOAD BALANCER HANYA DI S1
          # ===============================
          if dpid == 1:
              self.setup_group_lb(datapath)
  
      # ==================================================
      # LOAD BALANCING GROUP (S1 SAJA)
      # ==================================================
      def setup_group_lb(self, datapath):
          ofp = datapath.ofproto
          parser = datapath.ofproto_parser
  
          # -------------------------------
          # GROUP SELECT (S1 -> S2 / S3)
          # -------------------------------
          buckets = [
              parser.OFPBucket(
                  weight=50,
                  actions=[parser.OFPActionOutput(1)]  # ke s2
              ),
              parser.OFPBucket(
                  weight=50,
                  actions=[parser.OFPActionOutput(2)]  # ke s3
              )
          ]
  
          # HAPUS GROUP JIKA SUDAH ADA
          group_del = parser.OFPGroupMod(
              datapath=datapath,
              command=ofp.OFPGC_DELETE,
              type_=ofp.OFPGT_SELECT,
              group_id=1
          )
          datapath.send_msg(group_del)
  
          # TAMBAH GROUP BARU
          group_add = parser.OFPGroupMod(
              datapath=datapath,
              command=ofp.OFPGC_ADD,
              type_=ofp.OFPGT_SELECT,
              group_id=1,
              buckets=buckets
          )
          datapath.send_msg(group_add)
  
          # ==================================================
          # FLOW 1: LOAD BALANCING (h1 -> h2 SAJA)
          # ==================================================
          match = parser.OFPMatch(
              in_port=3,              # port h1 di s1
              eth_type=0x0800,
              ipv4_dst='10.0.0.2'
          )
          actions = [parser.OFPActionGroup(1)]
          self.add_flow(datapath, 10, match, actions)
  
          # ==================================================
          # FLOW 2: RETURN PATH (h2 -> h1, DETERMINISTIK)
          # ==================================================
          match = parser.OFPMatch(
              eth_type=0x0800,
              ipv4_dst='10.0.0.1'
          )
          actions = [parser.OFPActionOutput(3)]  # ke h1
          self.add_flow(datapath, 10, match, actions)
  
      # ==================================================
      # HELPER ADD FLOW
      # ==================================================
      def add_flow(self, datapath, priority, match, actions):
          ofp = datapath.ofproto
          parser = datapath.ofproto_parser
  
          inst = [parser.OFPInstructionActions(
              ofp.OFPIT_APPLY_ACTIONS, actions)]
  
          mod = parser.OFPFlowMod(
              datapath=datapath,
              priority=priority,
              match=match,
              instructions=inst
          )
          datapath.send_msg(mod)
  ```
  

  
