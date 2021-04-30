
  description = "Nimbo development shell";
  nixConfig.bash-prompt = "[nimbo-dev-shell]$ ";
  inputs = { flake-utils.url = "github:numtide/flake-utils"; };
  outputs = { self, nixpkgs, flake-utils, mach-nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system};
      in {
        devShell = pkgs.mkShell {
          buildInputs = with pkgs;
            with python3Packages; [
              python3

              awscli
              boto3
              click
              pydantic
              pyyaml
              requests
              setuptools
            ];
        };
      });
}
