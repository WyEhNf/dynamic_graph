#include "../solution.cpp"
#include <fstream>
#include <iostream>
int main(int argc,char** argv){if(argc!=2)return 2;std::ifstream f(argv[1]);int64_t a,b,gold;uint64_t d;size_t n=0;while(f>>a>>b>>d>>gold){auto actual=aicore_detail::priority_mul_div(a,b,d);if(actual!=gold){std::cerr<<a<<" "<<b<<" "<<d<<" "<<gold<<" "<<actual<<"\n";return 1;}++n;}std::cout<<n<<" exact priority arithmetic checks\n";return 0;}
