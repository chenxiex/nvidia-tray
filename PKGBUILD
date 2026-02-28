# Maintainer: anlorsp <anlor[at]anlor[dot]top>
pkgname=nvidia-tray-git
pkgver=0.r2.868ca11
pkgrel=1
pkgdesc="Linux tray application for ejecting NVIDIA GPU from PCI bus"
arch=('x86_64' 'aarch64')
url="https://github.com/chenxiex/nvidia-tray"
license=('GPL3')
depends=(
  'python'
  'python-pyudev'
  'python-gobject'
  'libappindicator'
  'polkit'
)
source=("${pkgname}::git+https://github.com/chenxiex/nvidia-tray.git")
sha256sums=('SKIP')

pkgver() {
  cd "${pkgname}"
  echo "0.r$(git rev-list --count HEAD).$(git rev-parse --short HEAD)"
}

package() {
  cd "${pkgname}"
  install -Dm755 nvidia_tray.py "${pkgdir}/usr/lib/nvidia-tray/nvidia-tray"
  
  # Install additional files
  install -Dm755 nvidia_eject_helper.py "${pkgdir}/usr/lib/nvidia-tray/nvidia-eject-helper"
  install -Dm644 io.github.anlorsp.nvidia-tray.policy "${pkgdir}/usr/share/polkit-1/actions/io.github.anlorsp.nvidia-tray.policy"
  install -Dm644 nvidia-tray.service "${pkgdir}/usr/lib/systemd/user/nvidia-tray.service"
  
  # Create executable wrapper
  mkdir -p "${pkgdir}/usr/bin"
  ln -s /usr/lib/nvidia-tray/nvidia-tray "${pkgdir}/usr/bin/nvidia-tray"
}
