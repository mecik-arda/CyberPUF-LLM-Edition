library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
use work.aes_paket.ALL;

entity tb_axi4_lite is
end entity tb_axi4_lite;

architecture sim of tb_axi4_lite is

    constant CLK_PERIOD        : time := 10 ns;
    constant C_S_AXI_DATA_WIDTH : integer := 32;
    constant C_S_AXI_ADDR_WIDTH : integer := 8;

    signal clk         : std_logic := '0';
    signal aresetn     : std_logic := '0';

    signal awaddr      : std_logic_vector(C_S_AXI_ADDR_WIDTH - 1 downto 0) := (others => '0');
    signal awprot      : std_logic_vector(2 downto 0) := (others => '0');
    signal awvalid     : std_logic := '0';
    signal awready     : std_logic;

    signal wdata       : std_logic_vector(C_S_AXI_DATA_WIDTH - 1 downto 0) := (others => '0');
    signal wstrb       : std_logic_vector(3 downto 0) := (others => '1');
    signal wvalid      : std_logic := '0';
    signal wready      : std_logic;

    signal bresp       : std_logic_vector(1 downto 0);
    signal bvalid      : std_logic;
    signal bready      : std_logic := '1';

    signal araddr      : std_logic_vector(C_S_AXI_ADDR_WIDTH - 1 downto 0) := (others => '0');
    signal arprot      : std_logic_vector(2 downto 0) := (others => '0');
    signal arvalid     : std_logic := '0';
    signal arready     : std_logic;

    signal rdata       : std_logic_vector(C_S_AXI_DATA_WIDTH - 1 downto 0);
    signal rresp       : std_logic_vector(1 downto 0);
    signal rvalid      : std_logic;
    signal rready      : std_logic := '1';

    component axi4_lite_sarmalayici is
        generic (
            C_S_AXI_DATA_WIDTH : integer := 32;
            C_S_AXI_ADDR_WIDTH : integer := 8;
            RO_CIFT_SAYISI       : integer := 16;
            INVERTER_SAYISI      : integer := 3;
            SAYICI_GENISLIGI      : integer := 20;
            SAYMA_DONGULERI       : integer := 1000;
            PUF_TEKRARLARI    : integer := 16
        );
        port (
            S_AXI_ACLK     : in  std_logic;
            S_AXI_ARESETN  : in  std_logic;
            S_AXI_AWADDR   : in  std_logic_vector(C_S_AXI_ADDR_WIDTH - 1 downto 0);
            S_AXI_AWPROT   : in  std_logic_vector(2 downto 0);
            S_AXI_AWVALID  : in  std_logic;
            S_AXI_AWREADY  : out std_logic;
            S_AXI_WDATA    : in  std_logic_vector(C_S_AXI_DATA_WIDTH - 1 downto 0);
            S_AXI_WSTRB    : in  std_logic_vector((C_S_AXI_DATA_WIDTH / 8) - 1 downto 0);
            S_AXI_WVALID   : in  std_logic;
            S_AXI_WREADY   : out std_logic;
            S_AXI_BRESP    : out std_logic_vector(1 downto 0);
            S_AXI_BVALID   : out std_logic;
            S_AXI_BREADY   : in  std_logic;
            S_AXI_ARADDR   : in  std_logic_vector(C_S_AXI_ADDR_WIDTH - 1 downto 0);
            S_AXI_ARPROT   : in  std_logic_vector(2 downto 0);
            S_AXI_ARVALID  : in  std_logic;
            S_AXI_ARREADY  : out std_logic;
            S_AXI_RDATA    : out std_logic_vector(C_S_AXI_DATA_WIDTH - 1 downto 0);
            S_AXI_RRESP    : out std_logic_vector(1 downto 0);
            S_AXI_RVALID   : out std_logic;
            S_AXI_RREADY   : in  std_logic;
            S_AXIS_TDATA   : in  std_logic_vector(31 downto 0) := (others => '0');
            S_AXIS_TVALID  : in  std_logic := '0';
            S_AXIS_TREADY  : out std_logic;
            S_AXIS_TLAST   : in  std_logic := '0';
            M_AXIS_TDATA   : out std_logic_vector(31 downto 0);
            M_AXIS_TVALID  : out std_logic;
            M_AXIS_TREADY  : in  std_logic := '0';
            M_AXIS_TLAST   : out std_logic
        );
    end component;

    procedure axi_write(
        signal aclk     : in std_logic;
        signal awaddr_s : out std_logic_vector;
        signal awvalid_s: out std_logic;
        signal awready_s: in std_logic;
        signal wdata_s  : out std_logic_vector;
        signal wvalid_s : out std_logic;
        signal wready_s : in std_logic;
        signal bvalid_s : in std_logic;
        signal bready_s : out std_logic;
        addr            : in std_logic_vector;
        data            : in std_logic_vector
    ) is
    begin
        wait until rising_edge(aclk);
        awaddr_s <= addr;
        awvalid_s <= '1';
        wdata_s <= data;
        wvalid_s <= '1';
        bready_s <= '1';

        wait until (awready_s = '1' and wready_s = '1') and rising_edge(aclk);
        awvalid_s <= '0';
        wvalid_s <= '0';

        if bvalid_s /= '1' then
            wait until bvalid_s = '1' and rising_edge(aclk);
        end if;
        wait for CLK_PERIOD;
    end procedure;

    procedure axi_read(
        signal aclk     : in std_logic;
        signal araddr_s : out std_logic_vector;
        signal arvalid_s: out std_logic;
        signal arready_s: in std_logic;
        signal rdata_s  : in std_logic_vector;
        signal rvalid_s : in std_logic;
        signal rready_s : out std_logic;
        addr            : in std_logic_vector;
        veri_cikis        : out std_logic_vector(31 downto 0)
    ) is
    begin
        wait until rising_edge(aclk);
        araddr_s <= addr;
        arvalid_s <= '1';
        rready_s <= '1';

        wait until arready_s = '1' and rising_edge(aclk);
        arvalid_s <= '0';

        if rvalid_s /= '1' then
            wait until rvalid_s = '1' and rising_edge(aclk);
        end if;
        veri_cikis := rdata_s;
        wait for CLK_PERIOD;
    end procedure;

begin

    clk <= not clk after CLK_PERIOD / 2;

    uut: axi4_lite_sarmalayici
        generic map (
            C_S_AXI_DATA_WIDTH => C_S_AXI_DATA_WIDTH,
            C_S_AXI_ADDR_WIDTH => C_S_AXI_ADDR_WIDTH,
            RO_CIFT_SAYISI       => 16,
            INVERTER_SAYISI      => 3,
            SAYICI_GENISLIGI      => 20,
            SAYMA_DONGULERI       => 50,
            PUF_TEKRARLARI    => 3
        )
        port map (
            S_AXI_ACLK    => clk,
            S_AXI_ARESETN => aresetn,
            S_AXI_AWADDR  => awaddr,
            S_AXI_AWPROT  => awprot,
            S_AXI_AWVALID => awvalid,
            S_AXI_AWREADY => awready,
            S_AXI_WDATA   => wdata,
            S_AXI_WSTRB   => wstrb,
            S_AXI_WVALID  => wvalid,
            S_AXI_WREADY  => wready,
            S_AXI_BRESP   => bresp,
            S_AXI_BVALID  => bvalid,
            S_AXI_BREADY  => bready,
            S_AXI_ARADDR  => araddr,
            S_AXI_ARPROT  => arprot,
            S_AXI_ARVALID => arvalid,
            S_AXI_ARREADY => arready,
            S_AXI_RDATA   => rdata,
            S_AXI_RRESP   => rresp,
            S_AXI_RVALID  => rvalid,
            S_AXI_RREADY  => rready
        );

    process
        variable read_data : std_logic_vector(31 downto 0);
        variable status_val : std_logic_vector(31 downto 0);
        variable poll_count : integer;
    begin
        report "========================================";
        report "AXI4-Lite Wrapper Testi";
        report "========================================";

        aresetn <= '0';
        wait for CLK_PERIOD * 10;
        aresetn <= '1';
        wait for CLK_PERIOD * 5;

        report "TEST 1: Kontrol register yazma/okuma...";

        axi_write(clk, awaddr, awvalid, awready, wdata, wvalid, wready, bvalid, bready,
                  x"00", x"00000000");
        axi_read(clk, araddr, arvalid, arready, rdata, rvalid, rready,
                 x"00", read_data);
        report "Control reg = " & to_hstring(read_data);

        report "TEST 2: Data-in register yazma...";

        axi_write(clk, awaddr, awvalid, awready, wdata, wvalid, wready, bvalid, bready,
                  x"08", x"AABBCCDD");
        axi_write(clk, awaddr, awvalid, awready, wdata, wvalid, wready, bvalid, bready,
                  x"0C", x"11223344");
        axi_write(clk, awaddr, awvalid, awready, wdata, wvalid, wready, bvalid, bready,
                  x"10", x"55667788");
        axi_write(clk, awaddr, awvalid, awready, wdata, wvalid, wready, bvalid, bready,
                  x"14", x"99001122");

        axi_read(clk, araddr, arvalid, arready, rdata, rvalid, rready,
                 x"08", read_data);
        report "Data-in[0] = " & to_hstring(read_data);

        report "TEST 3: PUF anahtar uretimi baslatiliyor (control bit 0)...";

        axi_write(clk, awaddr, awvalid, awready, wdata, wvalid, wready, bvalid, bready,
                  x"00", x"00000001");

        wait for CLK_PERIOD * 2;

        axi_write(clk, awaddr, awvalid, awready, wdata, wvalid, wready, bvalid, bready,
                  x"00", x"00000000");

        report "PUF uretimi bekleniyor...";

        poll_count := 0;
        loop
            wait for CLK_PERIOD * 100;
            axi_read(clk, araddr, arvalid, arready, rdata, rvalid, rready,
                     x"04", status_val);
            poll_count := poll_count + 1;

            if status_val(3) = '1' then
                report "Key expansion tamamlandi! (poll count: " & integer'image(poll_count) & ")";
                exit;
            end if;

            if poll_count > 50000 then
                report "TIMEOUT: PUF anahtar uretimi tamamlanamadi!" severity error;
                exit;
            end if;
        end loop;

        report "Status reg = " & to_hstring(status_val);

        report "PUF key okunuyor...";
        for i in 0 to 7 loop
            axi_read(clk, araddr, arvalid, arready, rdata, rvalid, rready,
                     std_logic_vector(to_unsigned(40 + i * 4, 8)), read_data);
            report "PUF Key[" & integer'image(i) & "] = " & to_hstring(read_data);
        end loop;

        report "TEST 4: Sticky status temizleme (control bit 4)...";

        axi_write(clk, awaddr, awvalid, awready, wdata, wvalid, wready, bvalid, bready,
                  x"00", x"00000010");
        wait for CLK_PERIOD * 2;
        axi_write(clk, awaddr, awvalid, awready, wdata, wvalid, wready, bvalid, bready,
                  x"00", x"00000000");

        axi_read(clk, araddr, arvalid, arready, rdata, rvalid, rready,
                 x"04", status_val);
        report "Status after clear = " & to_hstring(status_val);

        report "TEST 5: Decrypt baslatiliyor (control bit 1)...";

        axi_write(clk, awaddr, awvalid, awready, wdata, wvalid, wready, bvalid, bready,
                  x"00", x"00000002");
        wait for CLK_PERIOD * 2;
        axi_write(clk, awaddr, awvalid, awready, wdata, wvalid, wready, bvalid, bready,
                  x"00", x"00000000");

        poll_count := 0;
        loop
            wait for CLK_PERIOD * 10;
            axi_read(clk, araddr, arvalid, arready, rdata, rvalid, rready,
                     x"04", status_val);
            poll_count := poll_count + 1;

            if status_val(5) = '1' then
                report "Decrypt tamamlandi! (poll count: " & integer'image(poll_count) & ")";
                exit;
            end if;

            if poll_count > 10000 then
                report "TIMEOUT: Decrypt tamamlanamadi!" severity error;
                exit;
            end if;
        end loop;

        report "Decrypted data okunuyor...";
        for i in 0 to 3 loop
            axi_read(clk, araddr, arvalid, arready, rdata, rvalid, rready,
                     std_logic_vector(to_unsigned(24 + i * 4, 8)), read_data);
            report "Data-out[" & integer'image(i) & "] = " & to_hstring(read_data);
        end loop;

        report "TEST 6: Debug registerlari okuma...";
        axi_read(clk, araddr, arvalid, arready, rdata, rvalid, rready,
                 x"48", read_data);
        report "Debug Count A = " & to_hstring(read_data);

        axi_read(clk, araddr, arvalid, arready, rdata, rvalid, rready,
                 x"4C", read_data);
        report "Debug Count B = " & to_hstring(read_data);

        report "TEST 7: Gecersiz adres okuma...";
        axi_read(clk, araddr, arvalid, arready, rdata, rvalid, rready,
                 x"FC", read_data);
        report "Invalid addr data = " & to_hstring(read_data);

        if read_data = x"DEADBEEF" then
            report "Gecersiz adres dogru degerle dondu (DEADBEEF).";
        end if;

        report "========================================";
        report "AXI4-Lite TESTLERI TAMAMLANDI.";
        report "========================================";

        wait for CLK_PERIOD * 20;
        assert false report "Simulasyon tamamlandi." severity failure;
        wait;
    end process;

end architecture sim;
