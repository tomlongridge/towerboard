<?php

namespace App;

use Illuminate\Database\Eloquent\Model;

class Tower extends Model
{
    public function boards()
    {
        return $this->hasMany(Board::class);
    }

    public function getName()
    {
        return $this->attributes['town'] .
               ', ' . $this->attributes['county'] .
               ' (' . $this->attributes['country'] . ')' .
               ', ' . $this->attributes['dedication'] .
               ($this->attributes['area'] ? ', ' . $this->attributes['area'] : '') .
               ', ' . $this->attributes['num_bells'] .
               ($this->attributes['weight'] ? ', ' . $this->attributes['weight'] : '');
    }

    public function getNameHTML()
    {
        return '<strong>' . $this->attributes['town'] . '</strong>' .
               ', ' . $this->attributes['county'] .
               ' (' . $this->attributes['country'] . ')' .
               ', ' . $this->attributes['dedication'] .
               ($this->attributes['area'] ? ', ' . $this->attributes['area'] : '') .
               ', <strong>' . $this->attributes['num_bells'] . '</strong>' .
               ($this->attributes['weight'] ? ', ' . $this->attributes['weight'] : '');
    }
}
