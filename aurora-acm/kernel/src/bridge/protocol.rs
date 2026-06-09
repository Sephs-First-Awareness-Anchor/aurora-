// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// 8-byte bridge frame parser:
// [0xAC][0x58][X_u8][T_u8][N_u8][B_u8][A_u8][XOR]

use crate::acm::axes::AxisState;

const MAGIC0: u8 = 0xAC;
const MAGIC1: u8 = 0x58;
const FRAME_LEN: usize = 8;

pub struct FrameParser {
    buf: [u8; FRAME_LEN],
    pos: usize,
}

impl FrameParser {
    pub const fn new() -> Self {
        Self { buf: [0u8; FRAME_LEN], pos: 0 }
    }

    pub fn feed(&mut self, byte: u8) -> Option<AxisState> {
        if self.pos == 0 {
            if byte != MAGIC0 { return None; }
        } else if self.pos == 1 {
            if byte != MAGIC1 { self.pos = 0; return None; }
        }
        self.buf[self.pos] = byte;
        self.pos += 1;
        if self.pos == FRAME_LEN {
            self.pos = 0;
            self.try_decode()
        } else {
            None
        }
    }

    fn try_decode(&self) -> Option<AxisState> {
        let expected = self.buf[0] ^ self.buf[1] ^ self.buf[2]
            ^ self.buf[3] ^ self.buf[4] ^ self.buf[5] ^ self.buf[6];
        if expected != self.buf[7] { return None; }
        Some(AxisState {
            x: self.buf[2] as f32 / 255.0,
            t: self.buf[3] as f32 / 255.0,
            n: self.buf[4] as f32 / 255.0,
            b: self.buf[5] as f32 / 255.0,
            a: self.buf[6] as f32 / 255.0,
        })
    }
}
