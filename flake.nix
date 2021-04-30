{
  inputs = {
    mach-nix.url = "github:DavHau/mach-nix?rev=3.2.0";
  };
  outputs = { self, nixpkgs, flake-utils }: flake-utils.lib.eachDefaultSystem (system:
  let pkgs = nixpkgs.legacyPackages.${system};
  {
    devShell = pkgs.mkShell {
    };
  });
}
