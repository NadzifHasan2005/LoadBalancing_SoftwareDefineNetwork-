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
