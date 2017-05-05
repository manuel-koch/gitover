// This file is part of Gitover.
//
// Gitover is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Gitover is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Gitover. If not, see <http://www.gnu.org/licenses/>.
//
// Copyright 2017 Manuel Koch
//
import QtQuick 2.5
import Gitover 1.0
import "."

Item {
    id: root

    property int borderWidth:  10
    property int borderRadius: 4
    property var colors: []

    onBorderWidthChanged:  theCanvas.requestPaint()
    onBorderRadiusChanged: theCanvas.requestPaint()
    onColorsChanged:       theCanvas.requestPaint()

    Canvas {
        id: theCanvas
        width:  root.width
        height: root.height

        function pushColorToGradient(gradient,offset,spread,color,isLast) {
            var isFirst = (offset == 0)
            if( isFirst ) {
                gradient.addColorStop(0, color)
                gradient.addColorStop(spread*0.8, color)
            } else if( isLast ) {
                gradient.addColorStop(offset+spread*0.2, color)
                gradient.addColorStop(1.0, color)
            } else {
                gradient.addColorStop(offset+spread*0.2, color)
                gradient.addColorStop(offset+spread*0.8, color)
            }
            offset = isLast ? 1.0 : offset+spread
            return offset
        }

        onPaint: {
            var ctx = getContext("2d");
            var w = root.borderWidth
            var r = root.borderRadius

            ctx.clearRect(0,0,width,height)

            if( !w || !r || !root.colors.length ) {
                return
            }

            var s = 1/root.colors.length
            var linhgrad = ctx.createLinearGradient(0,0,width,0)
            var o = pushColorToGradient(linhgrad,0,s/2,root.colors[0])
            for( var i=1; i<root.colors.length; i++ ) {
                o = pushColorToGradient(linhgrad,o,s,root.colors[i])
            }
            pushColorToGradient(linhgrad,o,s/2,root.colors[0],true)

            var linvgrad = ctx.createLinearGradient(0,0,0,height)
            o = pushColorToGradient(linvgrad,0,s/2,root.colors[0])
            for( var i=1; i<root.colors.length; i++ ) {
                o = pushColorToGradient(linvgrad,o,s,root.colors[i])
            }
            pushColorToGradient(linvgrad,o,s/2,root.colors[0],true)

            ctx.save()

            // clip everything to rounded rect area
            ctx.beginPath()
            ctx.roundedRect(0,0,width,height,r,r)
            ctx.closePath()
            ctx.clip()

            // draw horizontal borders
            ctx.fillStyle = linhgrad
            ctx.fillRect(0,0,width,w)
            ctx.fillRect(0,height-w,width,height-w)

            // draw vertical borders
            ctx.fillStyle = linvgrad
            ctx.fillRect(0,0,w,height)
            ctx.fillRect(width-w,0,width,height)

            // revert every drawing inside a rounded rect area
            ctx.fillStyle = "transparent"
            ctx.globalCompositeOperation = "xor"
            ctx.beginPath()
            ctx.roundedRect(w-2,w-2,width-2*(w-2),height-2*(w-2),2,2)
            ctx.closePath()
            ctx.fill()

            ctx.restore()
        }
    }
}
