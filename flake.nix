{
  description = "Flake de desarrollo - MinExt";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs = { self, nixpkgs }: let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
      };
      packageOverrides= pkgs.callPackage ./python-packages.nix {};
      python = pkgs.python313.override { inherit packageOverrides; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = [
          pkgs.zsh
        ];

        packages = [
          (python.withPackages(p: [p.flask p.minizinc]))
        ];

        shellHook = ''
          echo "Entorno preparado"
          
        '';        
      };
    };
}
