// SHA-256 in a Web Worker. No secure-context requirement (LAN HTTP works).
const K = [
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
];
const INIT = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
const rot = (v,n) => (v >>> n) | (v << (32-n));
function sha256(input) {
  const msg = Array.from(new TextEncoder().encode(input));
  const bitLength = msg.length * 8;
  msg.push(128);
  while (msg.length % 64 !== 56) msg.push(0);
  for (const num of [Math.floor(bitLength / 4294967296), bitLength >>> 0])
    msg.push((num>>>24)&255,(num>>>16)&255,(num>>>8)&255,num&255);
  const H = INIT.slice(), W = new Array(64);
  for (let start=0; start<msg.length; start+=64) {
    for (let i=0; i<16; i++) {
      const j=start+4*i;
      W[i] = (msg[j]<<24 | msg[j+1]<<16 | msg[j+2]<<8 | msg[j+3])>>>0;
    }
    for (let i=16; i<64; i++) {
      const x=W[i-15], y=W[i-2];
      W[i]=(W[i-16]+(rot(x,7)^rot(x,18)^(x>>>3))+W[i-7]+
            (rot(y,17)^rot(y,19)^(y>>>10)))>>>0;
    }
    let [a,b,c,d,e,f,g,h]=H;
    for(let i=0;i<64;i++){
      const t1=(h+(rot(e,6)^rot(e,11)^rot(e,25))+((e&f)^(~e&g))+K[i]+W[i])>>>0;
      const t2=((rot(a,2)^rot(a,13)^rot(a,22))+((a&b)^(a&c)^(b&c)))>>>0;
      h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;
    }
    const round=[a,b,c,d,e,f,g,h];
    for(let i=0;i<8;i++) H[i]=(H[i]+round[i])>>>0;
  }
  return H.map(x=>x.toString(16).padStart(8,'0')).join('');
}
self.onmessage=function({data}){
  const {id,challenge,difficulty}=data;
  const prefix='0'.repeat(difficulty);
  for(let nonce=0;nonce<=10000000;nonce++){
    if(sha256(challenge+':'+nonce).startsWith(prefix)){
      self.postMessage({id,nonce,attempts:nonce+1});
      return;
    }
  }
  self.postMessage({error:'No proof found before the limit'});
};
